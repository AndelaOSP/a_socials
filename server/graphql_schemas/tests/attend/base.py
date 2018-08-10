from django.test import RequestFactory
from api.models import AndelaUserProfile, Category, Event, UserProxy, DeclinedInvite
from graphene.test import Client
from snapshottest.django import TestCase

from graphql_schemas.schema import schema


class BaseEventTestCase(TestCase):
    def setUp(self):
        category = Category.objects.create(
            id=1,
            name="Swimming Meetup",
            description="For people who want to be happy.",
            featured_image="https://cdn.elegantthemes.com/"
        )
        self.user1 = UserProxy.create_user({
            "username": "testuser",
            "first_name": "test",
            "last_name": "user",
            "email": "test@andela.com"
        })
        self.user2 = UserProxy.create_user({
            "username": "anotherUser",
            "first_name": "another",
            "last_name": "user",
            "email": "user2@andela.com"
        })
        self.user3 = UserProxy.create_user({
            "username": "thirdUser",
            "first_name": "third",
            "last_name": "user",
            "email": "user3@andela.com"
        })
        self.user4 = UserProxy.create_user({
            "username": "fourthUser",
            "first_name": "fourth",
            "last_name": "user",
            "email": "user4@andela.com"
        })
        self.andela_user1 = AndelaUserProfile.objects.create(
            google_id=123233,
            user=self.user1,
            user_picture="https://lh5.googleusercontent.com"
        )
        self.andela_user2 = AndelaUserProfile.objects.create(
            google_id=344445,
            user=self.user2,
            user_picture="https://lh5.googleusercontent.com"
        )
        self.andela_user3 = AndelaUserProfile.objects.create(
            google_id=84754,
            user=self.user3,
            user_picture="https://lh5.googleusercontent.com"
        )
        self.andela_user4 = AndelaUserProfile.objects.create(
            google_id=45444,
            user=self.user4,
            user_picture="https://lh5.googleusercontent.com"
        )
        self.event = Event.objects.create(
            id=1,
            title="Test",
            description="THis is a test event",
            venue="Epic Tower",
            creator=self.andela_user1,
            social_event=category,
            featured_image="https://cdn.elegantthemes.com/"
        )
        self.event2 = Event.objects.create(
            id=2,
            title="Test",
            description="THis is a another test event",
            venue="Ilupeju",
            creator=self.andela_user2,
            social_event=category,
            featured_image="https://cdn.eleganttes.com/"
        )
        self.attendance = Attend.objects.create(
            user=self.andela_user,
            event=self.event2
        )
        self.declinedEvent1 = DeclinedInvite.objects.create(
            user=self.andela_user2,
            event=self.event
        )
        self.declinedEvent2 = DeclinedInvite.objects.create(
            user=self.andela_user3,
            event=self.event
        ) 
        self.request = RequestFactory().get('/graphql')
        self.client = Client(schema)

    def tearDown(self):
        Category.objects.all().delete()
        AndelaUserProfile.objects.all().delete()
        Event.objects.all().delete()
        DeclinedInvite.objects.all().delete()
