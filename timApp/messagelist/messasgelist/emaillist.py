import re
from dataclasses import dataclass
from typing import List, Tuple, Optional
from urllib.error import HTTPError

from mailmanclient import Client, MailingList, Domain

from timApp.tim_app import app

_client: Optional[Client] = None
"""
A client object to utilize Mailmans REST API. Poke directly only when necessary, otherwise use via EmailListManager 
class. If this is None, mailmanclient-library has not been configured for use.
"""

if "MAILMAN_URL" not in app.config or "MAILMAN_PASS" not in app.config or "MAILMAN_PASS" not in app.config:
    # No configuration for Mailman found.
    print("No configuration found for Mailman connection.")
    pass
elif app.config['MAILMAN_URL'] == "" or app.config['MAILMAN_USER'] == "" or app.config['MAILMAN_PASS'] == "":
    # Only placeholder configuration for Mailman found.
    print("Server started without proper configuration for Mailman connection.")
else:
    # All Mailman configuration values exist and are something other than an empty string. We can initialize the
    # Client-object for connection.
    _client = Client(app.config['MAILMAN_URL'], app.config['MAILMAN_USER'], app.config['MAILMAN_PASS'])
    # TODO: Test connection somehow?


# VIESTIM Decorate class methods with @staticmethod unless the method would necessarily be needed for an instance of
#  the class. We wish to avoid instancing classes if possible.

# TODO: Handle situations where we can't contact Mailman server.

@dataclass
class EmailListManager:
    """Functionality for chosen email list management system Mailman 3. Handels everything else except things
    spesific to existing email lists."""

    domains: List[str]
    """Possible domains which can be used with our instance of Mailman."""

    @staticmethod
    def check_name_availability(name_candidate: str, domain: str) -> Tuple[Optional[bool], str]:
        """Search for a name from the pool of used email list names.

        :param domain: Domain to search for lists, which then are used to check name availability.
        :param name_candidate: The name to search for. The name needs to be a proper email list name,
        e.g. name@domain.org.
        :return: If we cannot get data from Mailman, return None and an explanation string. Return True if name is
        available. Return False if name was not available and a string to specify why.
        """
        if _client is None:
            return None, "No connection with email list server established."
        try:
            d = _client.get_domain(domain)
            mlists: List[MailingList] = d.get_lists()
            for name in [mlist.fqdn_listname for mlist in mlists]:
                if name_candidate == name:
                    return False, "Name is already in use."
            return True, "Name is available."
        except HTTPError:
            return None, "Connection to server failed."

    @staticmethod
    def check_name_requirements(name_candidate: str, domain: str) -> Tuple[Optional[bool], str]:
        """Checks name requirements spesific for email lists.

        :param domain: Domain to search for lists.
        :param name_candidate: Name to check for things and stuff. Mostly stuff.
        :return: Return None if connection to Mailman failed. Return True if all name requirements are met. Otherwise
        return False. In all cases, return an explanatory string.
        """
        em = EmailListManager

        # Check name is available.
        available, availability_explanation = em.check_name_availability(name_candidate, domain)
        if not available:
            return available, availability_explanation

        # Check if name is some reserved name.
        not_reserved, reserved_explanation = em.check_reserved_names(name_candidate)
        if not not_reserved:
            return not_reserved, reserved_explanation

        # Check name against name rules. These rules are also checked client-side.
        # VIESTIM: When other message list functionality exists, move this rule check there.
        within_rules, rule_explanation = em.check_name_rules(name_candidate)
        if not within_rules:
            return within_rules, rule_explanation

        return True, "Ok."

    @staticmethod
    def check_reserved_names(name_candidate: str) -> Tuple[bool, str]:
        """
        Check a name candidate against reserved names, e.g. postmaster.

        :param name_candidate: The name to be compared against reserved names.
        :return: Return True if name is not among reserved names. Otherwise return False.
        """
        # TODO: Implement a smarter query for reserved names. Now only compare against simple list for prototyping
        #  purposes. Maybe an external config file for known reserved names or something like that?
        #  Is it possible to query reserved names e.g. from Mailman or it's server?
        reserved_names: List[str] = ["postmaster", "listmaster", "admin"]
        if name_candidate in reserved_names:
            return False, "Name {0} is a reserved name.".format(name_candidate)
        else:
            return True, "Name is not reserved and can be used."

    @staticmethod
    def get_domain_names() -> List[str]:
        """Returns a list of all domain names.

        :return: A list of possible domain names.
        """
        # VIESTIM: Do we need to query the Mailman server every time? Should we cache this data locally and only
        #  query the Mailman server every now and then? Maybe even that server would inform us if new domains are
        #  added?
        if _client is None:
            return []
        try:
            domains: List[Domain] = _client.domains
            domain_names: List[str] = [domain.mail_host for domain in domains]
            return domain_names
        except HTTPError:
            return []

    @staticmethod
    def _set_domains() -> None:
        """Set possible domains. Searches possible domains from a configure file."""
        # TODO: Search the proper configuration file(s) for domains. Or should these be asked from the server instead?
        pass

    @staticmethod
    def create_new_list(name: str) -> None:
        """

        :param name: A full email list name, e.g. name@domain.org.
        :return:
        """
        print("testiprinti")
        print(name)

    @staticmethod
    def check_name_rules(name_candidate: str) -> Tuple[bool, str]:
        """Check if name candidate complies with naming rules.

        :param name_candidate:
        :return: Return True if name passes all rule checks. Otherwise return False.
        """
        # Be careful when checking regex rules. Some rules allow a pattern to exist, while prohibiting others. Some
        # rules prohibit something, but allow other things to exist. If the explanation for a rule is different than
        # the regex, the explanation is more likely to be correct.

        # Name is within length boundaries.
        lower_bound = 5
        upper_bound = 36
        if len(name_candidate) < lower_bound or upper_bound < len(name_candidate):
            return False, "Name is not within length boundaries. Name has to be at least {0} and at most {1} " \
                          "characters long".format(lower_bound, upper_bound)

        # Name has to start with a lowercase letter.
        start_with_lowercase = re.compile(r"^[a-z]")
        if start_with_lowercase.search(name_candidate) is None:
            return False, "Name has to start with a lowercase letter."

        # Name cannot have multiple dots in sequence.
        no_sequential_dots = re.compile(r"\.\.+")
        if no_sequential_dots.search(name_candidate) is not None:
            return False, "Name cannot have sequential dots"

        # Name cannot end in a dot
        no_end_in_dot = re.compile(r"\.$")
        if no_end_in_dot.search(name_candidate) is not None:
            return False, "Name cannot end in a dot."

        # Name can have only these allowed characters. This set of characters is an import from Korppi's character
        # limitations for email list names, and can probably be expanded in the future if desired.
        #     lowercase letters a - z
        #     digits 0 - 9
        #     dot '.'
        #     hyphen '-'
        #     underscore '_'
        # Notice the compliment usage of ^.
        allowed_characters = re.compile(r"[^a-z0-9.\-_]")
        if allowed_characters.search(name_candidate) is not None:
            return False, "Name contains forbidden characters."

        # Name has to include at least one digit.
        required_digit = re.compile(r"\d")
        if required_digit.search(name_candidate) is None:
            return False, "Name has to include at least one digit."

        return True, "Name meets all the naming rules."


@dataclass
class EmailList:
    """Class to aid with email list spesific functionality, such as attribute checking and changes.

    This class is designed to be used when an email list is expected to exits. Think operations like adding
    an email to an existing list etc. For operations other than that, use EmailListManager.
    """

    # VIESTIM: Would it be polite to return something as an indication how the operation went?

    @staticmethod
    def set_archive_type(listname: str, archive: bool) -> None:
        pass

    @staticmethod
    def delete_email(listname: str, email: str) -> str:
        """
        Destructive email unsubscribtion. After this function has performed, the email is no longer on the list. If
        you intended to perform a soft removal, use other function for a "soft" deletion.

        :param listname: The list where the email is being removed.
        :param email: The email being removed.
        :return: A string informing operation success.
        """
        if _client is None:
            return "There is no connection to Mailman server. No deletion can be attempted."
        mlist: Optional[MailingList]
        try:
            # This might raise HTTPError
            mlist = _client.get_list(fqdn_listname=listname)
            # This might raise ValueError
            mlist.unsubscribe(email=email)
            return "{0} has been removed from {1}".format(email, listname)
        except HTTPError:
            return "List {0} is not found or connection to list program was severed.".format(listname)
        except ValueError:
            return "Address {0} doesn't exist on {1}. No removal performed.".format(email, listname)

    @staticmethod
    def add_email(listname: str, email: str) -> None:
        pass

    @staticmethod
    def delete_list(fqdn_listname: str) -> str:
        """Delete a mailing list.

        :param fqdn_listname: The fully qualified domain name for the list, e.g. testlist1@domain.fi.
        :return: A string describing how the operation went.
        """
        if _client is None:
            return "There is no connection to Mailman server. No deletion can be attempted."

        try:
            # get_list() may raise HTTPError
            list_to_delete: MailingList = _client.get_list(fqdn_listname)
            list_to_delete.delete()
            return "The list {0} has been deleted.".format(fqdn_listname)
        except HTTPError:
            return "List {0} is not found or connection to server was severed." \
                   " No deletion occured.".format(fqdn_listname)

    @staticmethod
    def change_user_delivery_status(list_name: str, member_email: str, option: str, status: str) -> None:
        """ Change user's send or delivery status on an email list.

        :param list_name: List where we are changing delivery options.
        :param member_email: Which email's delivery options we are changing.
        :param option: Option can be 'delivery' or 'send'.
        :param status: A value that determs if option is 'enabled' or 'disabled'.
        :return:
        """
        # VIESTIM: We might want to change option and status parametrs from string to something like enum to rid
        #  ourselves from errors generated with typos.
        delivery = "delivery_status"
        if _client is None:
            return
        try:
            email_list = _client.get_list(list_name)
            member = email_list.get_member(member_email)
            member_preferences = member.preferences
            if option == delivery:
                # Viestim: This is just an idea how to go about changing user's delivery options. There exists
                #  frustratingly little documentation about this kind of thing, so this might not work. The idea
                #  originates from
                #  https://docs.mailman3.org/projects/mailman/en/latest/src/mailman/handlers/docs/owner-recips.html
                #  More information also at
                #  https://gitlab.com/mailman/mailman/-/blob/master/src/mailman/interfaces/member.py
                #
                # Change user's delivery off by setting "delivery_status" preference option to value "by_user"
                # or on by setting "delivery_status" preference option to "enabled".
                if status == "disabled":
                    member_preferences[delivery] = "by_user"
                if status == "enabled":
                    member_preferences[delivery] = "enabled"

                # Saving is required for changes to take effect.
                member_preferences.save()
            if option == "send":
                # TODO: Implement send status change.
                pass
        except HTTPError:
            pass
        return

    @staticmethod
    def get_user_delivery_option(email: str):
        pass
