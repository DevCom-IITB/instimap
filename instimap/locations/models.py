"""Models for Locations."""
from uuid import uuid4
from django.db import models
from locations.management.commands.adj_updater import UpdateAdjList

def get_url_friendly(name):
    """Converts the name to a url friendly string for use in `str_id`"""
    # Return blank in case None is passed
    if not name:
        return ""

    # Strip whitespaces and replace with dashes
    temp = "-".join(name.lower().split())

    # Remove special characters except dashes
    return "".join(c for c in temp if c.isalnum() or c == "-")

PERMISSION_CHOICES = (
    ("AddE", "Add Event"),
    ("UpdE", "Update Event"),
    ("DelE", "Delete Event"),
    ("UpdB", "Update Body"),
    ("Role", "Modify Roles"),
    ("VerA", "Verify Achievements"),
    ("AppP", "Moderate Post"),
    ("ModC", "Moderate Comment"),
)

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
    eatery = models.BooleanField(default=False)
    hostel = models.BooleanField(default=False)

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

class BodyRole(models.Model):
    """A role for a bodywhich can be granted to multiple users."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    time_of_creation = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=50)
    body = models.ForeignKey(
        "Body", on_delete=models.CASCADE, related_name="roles"
    )
    inheritable = models.BooleanField(default=False)
    # permissions = MultiSelectField(choices=PERMISSION_CHOICES)
    priority = models.IntegerField(default=0)
    official_post = models.BooleanField(default=True)
    permanent = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Body Role"
        verbose_name_plural = "Body Roles"
        ordering = ("body__name", "priority")

    def __str__(self):
        return self.body.name + " " + self.name

INSTITUTE_PERMISSION_CHOICES = (
    ("AddB", "Add Body"),
    ("DelB", "Delete Body"),
    ("BodyChild", "Modify Body-Child Relations"),
    ("Location", "Full control over locations"),
    ("Role", "Modify Institute Roles"),
    ("RoleB", "Modify roles for any body"),
)


class InstituteRole(models.Model):
    """An institute role which can be granted to multiple users."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    time_of_creation = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=50)
    description = models.CharField(max_length=100, blank=True)
    # permissions = MultiSelectField(choices=INSTITUTE_PERMISSION_CHOICES)

    class Meta:
        verbose_name = "Institute Role"
        verbose_name_plural = "Institute Roles"

    def __str__(self):
        return self.name


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
