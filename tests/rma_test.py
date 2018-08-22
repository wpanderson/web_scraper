__author__ = 'wpanderson'

import rma_query as r
from mock import patch
import unittest

@patch.object(r.Trogscraper, 'login')
def trogscraper_helper(mock_login):
    """
    Creates a Trogscraper object from rma_query

    :return: Trogscraper object
    """
    mock_login.return_value = 'SessionData'
    object = r.Trogscraper('charles', '123Password')

    return object

class TrogscraperInitTestCase(unittest.TestCase):
    """
    Unit tests for the initialization function in Trogscraper
    """

    @patch.object(r.Trogscraper, 'login')
    def test_standard(self, mock_login):
        """
        Test init to ensure that the proper values are initialized correctly
        when Trogscraper is created.
        """
        mock_login.return_value = 'SessionData'
        object = r.Trogscraper('charles', '123Password')

        self.assertEqual(object.session, 'SessionData')
        self.assertEqual(object.user, 'charles')
        self.assertEqual(object.password, '123Password')

class TrogscraperRmaThreadManagerTestCase(unittest.TestCase):
    """
    Unit tests for the rmaThreadManager function of Trogscraper
    """

    def test_standard(self):
        """

        :return:
        """

    def test_exception(self):
        """

        :return:
        """

unittest.main()