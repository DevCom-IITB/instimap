"""Models for Locations."""
from uuid import uuid4
from django.db import models
#from helpers.misc import get_url_friendly
from locations.management.commands.adj_updater import UpdateAdjList

from django.contrib.auth.models import User
from django.utils.timezone import now

def get_url_friendly(name):
    """Converts the name to a url friendly string for use in `str_id`"""
    # Return blank in case None is passed
    if not name:
        return ""

    # Strip whitespaces and replace with dashes
    temp = "-".join(name.lower().split())

    # Remove special characters except dashes
    return "".join(c for c in temp if c.isalnum() or c == "-")

class Location(models.Model):
    """A unique location, chiefly venues for events.

    Attributes:
        `lat` - Latitude
        'lng` - Longitude
    """

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    str_id = models.CharField(max_length=100, editable=False, null=True)
    time_of_creation = models.DateTimeField(auto_now_add=True)

    name = models.CharField(max_length=150)
    short_name = models.CharField(max_length=80, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    parent = models.ForeignKey("self", blank=True, null=True, on_delete=models.SET_NULL)
    parent_relation = models.CharField(max_length=50, blank=True, null=True)
    group_id = models.IntegerField(blank=True, null=True)

    pixel_x = models.IntegerField(blank=True, null=True)
    pixel_y = models.IntegerField(blank=True, null=True)
    lat = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    lng = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    reusable = models.BooleanField(default=False)
    connected_locs = models.TextField(blank=True, null=True)
    adjacent_locs = models.ManyToManyField(
        "locations.Location",
        through="LocationLocationDistance",
        related_name="adjacent_loc",
        blank=True,
    )

    def save(self, *args, **kwargs):  # pylint: disable =W0222
        self.str_id = get_url_friendly(self.short_name)
        if self.connected_locs:
            adj_data = self.connected_locs.split(",")
        else:
            # self.connected_locs = []
            adj_data = []

        if Location.objects.filter(name=self.name).exists():
            old_instance = Location.objects.filter(name=self.name).first()
            if old_instance.connected_locs:
                old_instance_adj = old_instance.connected_locs.split(",")
            else:
                old_instance_adj = []

            deletedConnections = list(set(old_instance_adj) - set(adj_data))

            UpdatedConnectionsLoc = []
            for loc in adj_data:
                if loc:
                    loc_object = Location.objects.filter(name=loc).first()
                    UpdatedConnectionsLoc.append(loc_object)
            UpdateAdjList().add_conns(
                self, UpdatedConnectionsLoc
            )  # Accounts for coordinates change also.

            deleted_connections_locs = []
            if deletedConnections:
                for loc in deletedConnections:
                    deleted_loc = Location.objects.filter(name=loc).first()
                    if deleted_loc is not None:
                        deleted_connections_locs.append(deleted_loc)
                UpdateAdjList().delete_connections(self, deleted_connections_locs)

        else:
            if adj_data:
                locs = adj_data
                connections = [
                    Location.objects.filter(name=x).first() for x in locs if x
                ]

                UpdateAdjList().add_conns(self, connections)

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        UpdateAdjList().delete_all_connections(self)
        super().delete(*args, **kwargs)

    def __str__(self):
        return (self.short_name if self.short_name else "") + " - " + self.name

    class Meta:
        verbose_name = "Location"
        verbose_name_plural = "Locations"
        ordering = ("name",)
        indexes = [
            models.Index(
                fields=[
                    "reusable",
                ]
            ),
            models.Index(fields=["reusable", "group_id"]),
        ]


class LocationLocationDistance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    location1 = models.ForeignKey(
        Location, on_delete=models.CASCADE, default=uuid4, related_name="lld1"
    )
    location2 = models.ForeignKey(
        Location, on_delete=models.CASCADE, default=uuid4, related_name="lld2"
    )
    distance = models.FloatField(default=100000000)

    class Meta:
        verbose_name = "Location-Location Distance"
        verbose_name_plural = "Location-Location Distances"
        

class UserProfile(models.Model):
    """Profile of a unique user."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    last_ping = models.DateTimeField(default=now)

    # Linked Django User object
    user = models.OneToOneField(
        User, related_name="profile", on_delete=models.CASCADE, null=True, blank=True
    )

    # Basic info from SSO
    name = models.CharField(max_length=50, blank=True)
    roll_no = models.CharField(max_length=30, null=True, blank=True)
    ldap_id = models.CharField(max_length=50, null=True, blank=True)
    profile_pic = models.URLField(null=True, blank=True)

    # Advanced info from SSO
    contact_no = models.CharField(max_length=30, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    department = models.CharField(max_length=30, null=True, blank=True)
    department_name = models.CharField(max_length=200, null=True, blank=True)
    degree = models.CharField(max_length=200, null=True, blank=True)
    degree_name = models.CharField(max_length=200, null=True, blank=True)
    join_year = models.CharField(max_length=5, null=True, blank=True)
    graduation_year = models.CharField(max_length=5, null=True, blank=True)
    hostel = models.CharField(max_length=100, null=True, blank=True)
    room = models.CharField(max_length=30, null=True, blank=True)

    # InstiApp feature fields
    active = models.BooleanField(default=True)
    followed_bodies = models.ManyToManyField(
        "bodies.Body", related_name="followers", blank=True
    )
    # InstiApp roles
    roles = models.ManyToManyField("roles.BodyRole", related_name="users", blank=True)
    former_roles = models.ManyToManyField(
        "roles.BodyRole",
        related_name="former_users",
        blank=True,
        through="UserFormerRole",
    )
    institute_roles = models.ManyToManyField(
        "roles.InstituteRole", related_name="users", blank=True
    )
    # community_roles = models.ManyToManyField('roles.CommunityRole', related_name='users', blank=True)
    # User exposed fields
    show_contact_no = models.BooleanField(default=False)
    fcm_id = models.CharField(max_length=200, null=True, blank=True)
    about = models.TextField(blank=True, null=True)
    android_version = models.IntegerField(default=0)
    website_url = models.URLField(blank=True, null=True)

BAN_REASON_CHOICHES = [
    ("IDF", "Unappropriate Comment"),
    ("Buy&Sell", "Unappropriate Activity in Buy and Sell"),
    ("Graduated ", "Passed out from Institute"),
    ("InstiBan", "Banned by Insittute Authority"),
]

BAN_DURATION_CHOICES = [
    ("1 month", "One Month"),
    ("3 months", "Three Months"),
    ("6 months", "Six Months"),
    ("12 months", "Twelve Months"),
    ("Permanent", "Permanent"),
]

class SSOBan(models.Model):
    """Bans imposed on students to access any SSO required View."""

    id = models.UUIDField(primary_key=True, default=uuid4, blank=False)
    banned_user = models.ForeignKey(
        to="users.UserProfile",
        related_name="banned_user",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    time_of_creation = models.DateTimeField(auto_now_add=True)
    reason = models.CharField(max_length=30, choices=BAN_REASON_CHOICHES)
    detailed_reason = models.TextField(blank=True)
    duration_of_ban = models.CharField(max_length=20, choices=BAN_DURATION_CHOICES)
    banned_by = models.ForeignKey(
        to="users.UserProfile",
        related_name="banned_by",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    banned_user_ldapid = models.CharField(max_length=20, blank=True, null=True)

    def save(self, *args, **kwargs) -> None:
        if self.banned_user_ldapid:
            self.banned_user = UserProfile.objects.get(ldap_id=self.banned_user_ldapid)
        return super().save(*args, **kwargs)
    
class Body(models.Model):
    """An organization or club which may conduct events."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    str_id = models.CharField(max_length=50, editable=False, null=True)
    time_of_creation = models.DateTimeField(auto_now_add=True)
    time_of_modification = models.DateTimeField(auto_now=True)

    name = models.CharField(max_length=50)
    canonical_name = models.CharField(max_length=50, blank=True)
    short_description = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    website_url = models.URLField(blank=True, null=True)
    image_url = models.URLField(blank=True, null=True)
    cover_url = models.URLField(blank=True, null=True)
    blog_url = models.URLField(null=True, blank=True)

    def save(self, *args, **kwargs):  # pylint: disable=W0222
        self.str_id = get_url_friendly(
            self.name if not self.canonical_name else self.canonical_name
        )
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return "/org/" + self.str_id

    class Meta:
        verbose_name = "Body"
        verbose_name_plural = "Bodies"
        ordering = ("name",)
