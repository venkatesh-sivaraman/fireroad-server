from django.db import models
from django.forms import ModelForm
from django.contrib.auth.models import User

class UserForm(ModelForm):
    class Meta:
        model = User
        fields = ['username', 'password']

class Student(models.Model):
    user = models.OneToOneField(User, null=True, on_delete=models.CASCADE)
    academic_id = models.CharField(max_length=50)
    current_semester = models.CharField(max_length=25, default='0')
    name = models.CharField(max_length=40, default="")
    semester_update_date = models.DateTimeField(auto_now=True)
    unique_id = models.CharField(max_length=50, default="")

    favorites = models.CharField(max_length=2000, default="")
    progress_overrides = models.CharField(max_length=3000, default="")
    notes = models.TextField(default="")

    def __str__(self):
        return "ID {}, in {} ({} user)".format(self.academic_id, self.current_semester, self.user)

    def has_approved_client(self, client):
        """Checks whether this student has approved the given APIClient object."""
        return self.approved_clients.filter(pk=client.pk).exists()

    def approve_client(self, client):
        """Approves the given APIClient object."""
        self.approved_clients.add(client)

class OAuthCache(models.Model):
    state = models.CharField(max_length=50)
    nonce = models.CharField(max_length=50)
    current_semester = models.CharField(max_length=25, default='0')
    date = models.DateTimeField(auto_now_add=True)

    # Store redirect URI if provided
    redirect_uri = models.CharField(max_length=200, null=True)

class TemporaryCode(models.Model):
    code = models.CharField(max_length=100)
    access_info = models.CharField(max_length=500)
    date = models.DateTimeField(auto_now_add=True)

class APIClient(models.Model):
    """Defines a single client for the FireRoad API and its access permissions.

    When adding new permissions, all the helper methods of this class must be updated."""
    name = models.CharField(max_length=100)
    contact_name = models.CharField(max_length=100)
    contact_email = models.CharField(max_length=100)

    approved_users = models.ManyToManyField("Student", related_name="approved_clients")

    # Permissions that the API client may be granted
    can_view_academic_id = models.BooleanField(default=False)
    can_view_student_info = models.BooleanField(default=False)
    can_edit_student_info = models.BooleanField(default=False)

    can_view_roads = models.BooleanField(default=False)
    can_edit_roads = models.BooleanField(default=False)
    can_delete_roads = models.BooleanField(default=False)

    can_view_schedules = models.BooleanField(default=False)
    can_edit_schedules = models.BooleanField(default=False)
    can_delete_schedules = models.BooleanField(default=False)

    can_view_recommendations = models.BooleanField(default=False)

    def num_permissions(self):
        """Returns the number of permissions that this client is granted."""
        return (int(self.can_view_academic_id) + int(self.can_view_student_info) +
                int(self.can_edit_student_info) + int(self.can_view_roads) +
                int(self.can_edit_roads) + int(self.can_delete_roads) +
                int(self.can_view_schedules) + int(self.can_edit_schedules) +
                int(self.can_delete_schedules))

    def permissions_flag(self):
        """Returns an integer representation of the permissions this client is granted."""
        flag = 0
        flag |= self.can_view_academic_id << 0
        flag |= self.can_view_student_info << 1
        flag |= self.can_edit_student_info << 2
        flag |= self.can_view_roads << 3
        flag |= self.can_edit_roads << 4
        flag |= self.can_delete_roads << 5
        flag |= self.can_view_schedules << 6
        flag |= self.can_edit_schedules << 7
        flag |= self.can_delete_schedules << 8
        flag |= self.can_view_recommendations << 9
        return flag

    @staticmethod
    def from_permissions_flag(flag):
        """Creates a *temporary* APIClient object with the permissions granted by the given
        flag."""
        client = APIClient()
        client.can_view_academic_id = (flag & (1 << 0)) != 0
        client.can_view_student_info = (flag & (1 << 1)) != 0
        client.can_edit_student_info = (flag & (1 << 2)) != 0
        client.can_view_roads = (flag & (1 << 3)) != 0
        client.can_edit_roads = (flag & (1 << 4)) != 0
        client.can_delete_roads = (flag & (1 << 5)) != 0
        client.can_view_schedules = (flag & (1 << 6)) != 0
        client.can_edit_schedules = (flag & (1 << 7)) != 0
        client.can_delete_schedules = (flag & (1 << 8)) != 0
        client.can_view_recommendations = (flag & (1 << 9)) != 0
        return client

    @staticmethod
    def universal_permission_flag():
        """Creates a flag representing all available permissions."""
        flag = 0
        for i in range(10):
            flag |= 1 << i
        return flag

    def _format_abilities_list(self, abilities):
        if len(abilities) > 1:
            abilities[-1] = "and " + abilities[-1]
        if len(abilities) == 2:
            text = " ".join(abilities)
        else:
            text = ", ".join(abilities)

        return text[0].upper() + text[1:].lower()

    def permissions_descriptions(self):
        """Returns a list of strings corresponding to permissions that this client is granted."""
        items = []
        if self.can_view_academic_id:
            items.append("View your academic email address")
        if self.can_view_student_info or self.can_edit_student_info:
            abilities = []
            if self.can_view_student_info:
                abilities.append("view")
            if self.can_edit_student_info:
                abilities.append("edit")
            items.append("{} your profile information in FireRoad".format(
                self._format_abilities_list(abilities)))
        if self.can_view_roads or self.can_edit_roads or self.can_delete_roads:
            abilities = []
            if self.can_view_roads:
                abilities.append("view")
            if self.can_edit_roads:
                abilities.append("edit")
            if self.can_delete_roads:
                abilities.append("delete")
            items.append("{} your roads".format(
                self._format_abilities_list(abilities)))
        if self.can_view_schedules or self.can_edit_schedules or self.can_delete_schedules:
            abilities = []
            if self.can_view_schedules:
                abilities.append("view")
            if self.can_edit_schedules:
                abilities.append("edit")
            if self.can_delete_schedules:
                abilities.append("delete")
            items.append("{} your schedules".format(
                self._format_abilities_list(abilities)))
        if self.can_view_recommendations:
            items.append("View your recommendations")
        return items

    def __str__(self):
        return "{} (by {}) - {} permissions".format(self.name, self.contact_name,
                                                    self.num_permissions())

class RedirectURL(models.Model):
    """Defines a registered redirect URL for the login endpoint."""
    label = models.CharField(max_length=50)
    url = models.CharField(max_length=200)
    client = models.ForeignKey(APIClient, null=True, on_delete=models.CASCADE)

    def __str__(self):
        return self.label + ": " + self.url

