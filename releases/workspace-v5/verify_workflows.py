"""Validate actual OpenEnv protocol/reset/isolation without reference solutions."""
import argparse
import json
from pathlib import Path
import subprocess
import time
import uuid

BRIDGE = r'''
import json,sys,time,urllib.request
from websockets.sync.client import connect
for _ in range(120):
    try:
        urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=1)
        break
    except Exception: time.sleep(1)
else: raise RuntimeError('server health deadline')
with urllib.request.urlopen('http://127.0.0.1:8000/schema') as response:
    print(json.dumps({'schema':json.load(response)}),flush=True)
with connect('ws://127.0.0.1:8000/ws',open_timeout=30,max_size=2**22) as ws:
    for line in sys.stdin:
        ws.send(line.strip())
        print(ws.recv(timeout=180),flush=True)
'''


def verify(image, task_id, admission=False):
    name = 'artifact-release-check-' + uuid.uuid4().hex[:12]
    bridge = None
    checks = []
    started = time.monotonic()
    try:
        subprocess.run(['docker','run','-d','--rm','--name',name,'--platform','linux/amd64',
                        '--network','none','--cpus','2','--memory','8g','--pids-limit','512',
                        '--security-opt','no-new-privileges','--cap-drop','ALL',
                        '--cap-add','SETUID','--cap-add','SETGID','--cap-add','CHOWN',
                        '--cap-add','DAC_OVERRIDE','--cap-add','KILL',image],
                       check=True,capture_output=True,timeout=180)
        admission_report = None
        if admission:
            health = "import time,urllib.request\nfor _ in range(120):\n try:\n  urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=1); break\n except Exception: time.sleep(1)\nelse: raise RuntimeError('server health deadline')\n"
            subprocess.run(['docker','exec',name,'python3','-c',health],check=True,capture_output=True,timeout=150)
            result = subprocess.run(['docker','exec',name,'openenv','validate',
                                     '--url','http://127.0.0.1:8000','--json'],
                                    text=True,capture_output=True,timeout=180)
            assert result.returncode == 0, result.stdout + result.stderr
            admission_report = json.loads(result.stdout)
            checks.append('pinned-openenv-cli-validate-url')
        bridge = subprocess.Popen(['docker','exec','-i',name,'python3','-u','-c',BRIDGE],
                                  stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        first = bridge.stdout.readline()
        assert first and isinstance(json.loads(first)['schema'],dict), 'schema is unavailable'
        schema = json.loads(first)['schema']
        checks.append('schema-served')

        def call(kind, data):
            bridge.stdin.write(json.dumps({'type':kind,'data':data})+'\n')
            bridge.stdin.flush()
            line = bridge.stdout.readline()
            assert line, 'bridge ended before response'
            response = json.loads(line)
            assert response.get('type') == 'observation', response
            return response['data']

        reset = call('reset',{'task_id':task_id,'seed':101})
        assert reset['observation']['task_id'] == task_id
        assert reset['observation']['output'] and not reset.get('done')
        checks.append('reset-correct-task')
        shell = call('step',{'operation':'shell','command':
                     "printf 'protocol-check\\n'; id -u; test ! -r /opt/arena/bundles.json && test ! -r /opt/arena/runtime_server.py"})
        assert shell['observation']['exit_code'] == 0
        assert 'protocol-check\n2000' in shell['observation']['output']
        assert not shell.get('done')
        checks.append('unprivileged-shell-protected-grader')
        negative = call('step',{'operation':'finish'})
        assert negative.get('done') and negative.get('reward') == 0
        checks.append('unfinished-artifacts-score-zero')
        cached = call('step',{'operation':'finish'})
        assert cached == negative
        checks.append('terminal-result-cached')
        second = call('reset',{'task_id':task_id,'seed':307})
        assert second['observation']['task_id'] == task_id and not second.get('done')
        assert call('step',{'operation':'finish'}).get('reward') == 0
        checks.append('reset-restores-unsolved-inputs')
        return {'task_id':task_id,'passed':True,'checks':checks,'schema':schema,
                'admission':admission_report,'seconds':time.monotonic()-started}
    finally:
        if bridge is not None:
            bridge.kill()
            bridge.communicate(timeout=10)
        subprocess.run(['docker','rm','-f',name],capture_output=True,timeout=30)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--bundles',type=Path,default=Path(__file__).with_name('bundles.json'))
    args = parser.parse_args()
    bundles = json.loads(args.bundles.read_text())
    assert 1 <= len(bundles) <= 50
    tasks = [b['task_id'] for b in bundles]
    assert len(set(tasks)) == len(tasks)
    report = {'image':args.image,'mode':'protocol-reset-isolation-no-reference-solutions','tasks':[],'passed':False}
    try:
        for index,task_id in enumerate(tasks):
            report['tasks'].append(verify(args.image,task_id,admission=index==0))
        report['schema'] = report['tasks'][0]['schema']
        assert all(t['schema'] == report['schema'] for t in report['tasks'])
        report['passed'] = True
    finally:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'passed':report['passed'],'tasks':len(report['tasks'])}))


if __name__ == '__main__':
    main()
