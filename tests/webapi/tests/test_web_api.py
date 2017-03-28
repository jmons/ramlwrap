
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

import json
from django.test import TestCase, Client

import logging
from django.contrib.auth.models import User


class WebAPITestCase(TestCase):
    """
    The purpose of this test case is to look at the behaviour of a webapp api, i.e. how an app that
    uses cookie / session based auth responds to ramlwrap (and the correct location of csrf exempt
    if needed)
    """

    client = None
 
    def setUp(self):
        logging.disable(logging.CRITICAL)
        self.client = Client()
        
    def tearDown(self):
        logging.disable(logging.NOTSET)

    def _get_testfunc(self):
        response = self.client.get('/web_app_tests/get')

        return response

    def _post_testfunc(self):
        response = self.client.post('/web_app_tests/post', 
                                    data=json.dumps({"data": "val"}), 
                                    content_type="application/json")

        return response

    def _run_test(self, server_call):

        """
        This test is to specifically test a logged in api auth using djangos default session 
        When called by a get
        """
        
        # call protected api (expect an error)
        response = server_call()
        
        # this should be a redirect to login, as per @login_required
        self.assertEqual(response.status_code, 302) 
        
        # make a user so I can login with it
        username = u"john"
        password = "johnpassword"
        User.objects.create_user(username, 'lennon@example.com', password)

        # Call login api with post data
        self.client.login(username=username, password=password)
    
        # now call protected api
        response = server_call()
        
        self.assertEqual(response.status_code, 200)

        retrieved_data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(retrieved_data['status'], u"ok")
        self.assertEqual(retrieved_data['logged_in_user'], username)

        # call logout
        self.client.logout()

        # now for the hell of it, call protected api again (expect an error)
        response = server_call()
        # this should be a redirect to login, as per @login_required
        self.assertEqual(response.status_code, 302) 
        
    def test_logined_call_get(self):
        """ Test when using a get request """
        self._run_test(self._get_testfunc)

    def test_logined_call_post(self):
        """ Test when using a POST request """
        self._run_test(self._post_testfunc)