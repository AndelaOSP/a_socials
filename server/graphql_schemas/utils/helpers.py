import os
import datetime
import logging
import pytz
import dotenv
import dateutil.parser as parser
from time import sleep
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage

from api.slack import generate_simple_message, notify_user
from api.utils.oauth_helper import get_auth_url
from api.models import Interest, Attend, Event
from googleapiclient.discovery import build
from google.cloud import storage

from django.conf import settings


def is_not_admin(user):
    """
    This function checks if a user is not an admin user.
        :param user
    """
    return not user.is_superuser


def update_instance(instance, args, exceptions=['id']):
    """
        This function was created to help clean up input to be used for
        updatingobjects. Typically the input from the graphql endpoint comes
        with unwanted extras such as uniqueids that are not required or will
        cause an error when updating an object hence the exceptionparameter.
        Args:
            instace(dict): the instances to be saved
            args: the args
            exceptions(list)
        Returns
            instance(dict): the instance that was saved
    """
    if instance:
        [setattr(instance, key, value)
            for key, value in args.items() if key not in exceptions]
        instance.save()
    return instance


class UnauthorizedCalendarError(Exception):
    """
        Calendar Error class for unauthorized calendar.
    """

    def __init__(self, message='', auth_url=''):
        super().__init__(message)
        self.message = message
        self.auth_url = auth_url


def raise_calendar_error(user_profile):
    """
        Raise calendar error for Users with no access tokens
        Args:
            user_profile(dict): the profile of the user accessing the calendar
        Returns
            instance(dict): Unauthorized error
    """
    auth_url = get_auth_url(user_profile)
    raise UnauthorizedCalendarError(message="Calendar API not authorized",
                                    auth_url=auth_url)


async def send_calendar_invites(andela_user, event):
    """
        Send calendar invites asynchronously
        Args:
            andela_user(dict): the user to be invited
            event(dict): the event to invite user for
        Returns
            instance(func): send invite use user
    """
    invitees = Interest.objects.filter(follower_category=event.social_event)
    invitee_list = [{'email': invitee.follower.user.email}
                    for invitee in invitees]
    payload = build_event(event, invitee_list)

    calendar = build('calendar', 'v3', credentials=andela_user.credential)
    if settings.ENVIRONMENT == "production":
        calendar.events().insert(calendarId='primary', sendNotifications=True,
                                 body=payload).execute()


def build_event(event, invitees, recurring=False):
    """
        Build event payload
        Args:
            invitees(dict): the user to be invited
            recurring(dict): the event to invite user for
        Returns
            calendar_event(list): the callendar event
    """
    start_date = parser.parse(str(event.start_date)).isoformat()
    end_date = parser.parse(str(event.end_date)).isoformat()
    calendar_event = {
        'summary': event.title,
        'location': event.venue,
        'description': event.description,
        'start': {
            'dateTime': start_date,
            'timeZone': event.timezone
        },
        'end': {
            'dateTime': end_date,
            'timeZone': event.timezone
        },
        'attendees': invitees,
    }
    if recurring:
        recurrence_end_date = parser.parse(str(event.recurrence.end_date))
        RFC2445_date = recurrence_end_date.strftime("%Y%m%dT%H%M%SZ")
        frequency = event.recurrence.frequency
        calendar_event['recurrence'] = [
            f'RRULE:FREQ={frequency};UNTIL={RFC2445_date}'
        ]
    return calendar_event


def validate_event_dates(input, date_to_validate):
    """
        Validate event dates
        Args:
            input(dict): the input to get the details
            date_to_validate(dict): the date to be validated
        Returns
            normalize_dates(tuple): the validated dates
    """
    event_tz = input.get('start_date').tzinfo
    start_date = input.get('start_date')
    if date_to_validate == 'recurrent_date' and input.get('recurring'):
        end_date = input.get('recurrence_end_date')
    else:
        end_date = input.get('end_date')
    today_date = datetime.datetime.now(event_tz)
    return normalize_dates(end_date, start_date, today_date)


def normalize_dates(end_date, start_date, today_date):
    """
        Validate the dates relatively to each other
        Args:
            end_date(date): the end date
            start_date(date): the start date
            today_date(date): the date for today
        Returns
            (dict): success or failure message
    """
    if start_date < today_date or end_date < today_date:
        return {'status': False, 'message': 'Sorry, you cannot enter a past date'}
    elif end_date < start_date:
        return {'status': False, 'message': 'Sorry, end date must be after start date'}
    else:
        return {'status': True, 'message': 'Validation successful'}


def not_valid_timezone(timezone):
    """
        validate timezone
        Args:
            timezone(date): the timezone to be validated
        Returns
            (bool): false if timezone not in all timezone
    """
    return timezone not in pytz.all_timezones

def _safe_filename(filename):
    """
    Generates a safe filename that is unlikely to collide with existing objects
    in Google Cloud Storage.
    Args:
        filename(dict): the file to be changed
    Returns
        (file): is transformed into ``filename-YYYY-MM-DD-HHMMSS.ext``
    """
    date = datetime.datetime.utcnow().strftime("%Y-%m-%d-%H%M%S")
    basename, extension = filename.rsplit('.', 1)
    return "{0}-{1}.{2}".format(basename, date, extension)


def validate_image(file_obj):
    """
    Validate the image.
    Args:
        file_obj(dict): the file data
    Returns
        (error): error if not valid image
    """
    filesize = file_obj.size
    megabyte_limit = 2.0
    extensions = {".jpg", ".png", ".gif", ".jpeg"}
    if filesize > megabyte_limit*1024*1024:
        raise ValidationError("Max file size is %sMB" % str(megabyte_limit))
    if not any(file_obj.name.lower().endswith(key) for key in extensions):
        raise ValidationError("You can only upload image files")


def upload_image_file(uploaded_file):

    """
    upload image file
    Args:
        uploaded_file(dict): file to be uploaded
    Returns
        (url): url of the image uploaded
    """
    if settings.ENVIRONMENT == "production":
        """
        Uploads a file to a given Cloud Storage bucket and
        returns the public url to the new object.
        """

        # Authenticate storage client
        storage_client = storage.Client.from_service_account_json(
            os.getenv('GOOGLE_CLOUD_CREDENTIALS_PATH')
        )

        filename = _safe_filename(uploaded_file.name)

        bucket = storage_client.get_bucket(
            os.getenv('GOOGLE_CLOUD_BUCKET_NAME'))
        blob = bucket.blob(filename)

        blob.upload_from_file(uploaded_file)
        url = blob.public_url

        return url

    if settings.ENVIRONMENT == "development":
        validate_image(uploaded_file)
        fs = FileSystemStorage()
        safe_filename = _safe_filename(uploaded_file.name)
        filename = fs.save(safe_filename, uploaded_file)
        url = f"{dotenv.get('IMAGE_BASE_URL')}/static{fs.url(filename)}"
        return url


async def send_bulk_update_message(event_instance, message, notification_text):

    """
    send bulk messages to the users on slack
    Args:
        event_instance(dict): the instance of the event
        message(dict): message to be sent to users on slack
        notification_text(str): the notification text to display
    Returns
        (none): send the slack message
    """
    attendees = Attend.objects.filter(
        event=event_instance, status="attending")
    for attendee in attendees:
        slack_id = attendee.user.slack_id
        if slack_id:
            message = generate_simple_message(message)
            slack_response = notify_user(
                message, slack_id, text=notification_text)

            if slack_response["ok"] is False and slack_response["headers"]["Retry-After"]:
                delay = int(slack_response["headers"]["Retry-After"])
                logging.info("Rate limited. Retrying in " + str(delay) + " seconds")
                sleep(delay)
                notify_user(
                    message, slack_id, notification_text)
            elif not slack_response['ok']:
                logging.warning(slack_response)


def add_event_to_calendar(andela_user, event, recurring=False):
    """
    Adds an event to a user's calendar
    Args:
        andela_user(dict): the user to have the event in calendar
        event(dict): the event to be saved in the calendar
        recurring(bool): bool to re-occur
    Returns
        save event on user's calendar
    """
    calendar = build('calendar', 'v3', credentials=andela_user.credential)
    event_details = build_event(event, [], recurring)
    created_event = calendar.events().insert(
            calendarId='primary', body=event_details).execute()
    event.event_id_in_calendar = created_event['id']
    event.save()


def update_event_status_on_calendar(andela_user, event):
    """
    Adds an event to a user's calendar
    Args:
        andela_user(dict): the user to update the event in calendar
        event(dict): the event to be updated in the calendar
    Returns
        update event on user's calendar
    """
    try:
        event_id = event.event_id_in_calendar
        host_calendar = build('calendar', 'v3', credentials=event.creator.credential)
        attendee_calendar = build('calendar', 'v3', credentials=andela_user.credential)
        event_in_calendar = host_calendar.events().get(calendarId='primary', eventId=event_id).execute()
        attendees = event_in_calendar['attendees']
        attendees.append({'email': andela_user.user.email})
        host_calendar.events().patch(
            calendarId='primary',
            eventId=event_id,
            body=event_in_calendar
        ).execute()
        last_attendee = event_in_calendar['attendees'][-1]
        last_attendee['responseStatus'] = 'accepted'
        attendee_calendar.events().patch(
            calendarId='primary',
            eventId=event_id,
            body=event_in_calendar
        ).execute()
    except KeyError:
        event_in_calendar['attendees'] = [{'email': andela_user.user.email}]
        host_calendar.events().patch(
            calendarId='primary',
            eventId=event_id,
            body=event_in_calendar
        ).execute()
        last_attendee = event_in_calendar['attendees'][-1]
        last_attendee['responseStatus'] = 'accepted'
        attendee_calendar.events().patch(
            calendarId='primary',
            eventId=event_id,
            body=event_in_calendar
        ).execute()


def remove_event_from_all_calendars(andela_user, event):
    """
    Remove an event from all calendars
    Args:
        andela_user(list): The user data of the person removing the event
        event(list): The event to be removed from the calendar
    Returns: None
    """
    eventId = event.event_id_in_calendar
    calendar = build('calendar', 'v3', credentials=andela_user.credential)
    calendar.events().delete(calendarId='primary', eventId=eventId).execute()
