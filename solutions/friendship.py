"""Reference repair for validating the Django task; excluded from images."""
from pathlib import Path

path = Path("/workspace/repo/friends/models.py")
text = path.read_text()
text = text.replace("class Friendship(models.Model):", '''class FriendshipManager(models.Manager):
    def _pair(self, user1, user2):
        return self.filter(
            models.Q(from_user=user1, to_user=user2)
            | models.Q(from_user=user2, to_user=user1)
        )

    def friends_for_user(self, user):
        return [
            {"friend": row.to_user if row.from_user_id == user.pk else row.from_user,
             "friendship": row}
            for row in self.filter(models.Q(from_user=user) | models.Q(to_user=user))
        ]

    def are_friends(self, user1, user2):
        return self._pair(user1, user2).exists()

    def remove(self, user1, user2):
        self._pair(user1, user2).delete()


def friend_set_for(user):
    return {row["friend"] for row in Friendship.objects.friends_for_user(user)}


class Friendship(models.Model):
    objects = FriendshipManager()
''')
text += '''

def _friendship_removed(sender, instance, **kwargs):
    FriendshipInvitation.objects.filter(
        from_user=instance.from_user, to_user=instance.to_user
    ).exclude(status="8").update(status="8")


signals.post_delete.connect(_friendship_removed, sender=Friendship)
'''
path.write_text(text)
