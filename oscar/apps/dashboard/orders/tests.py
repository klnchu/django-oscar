import httplib
from django_dynamic_fixture import new, get, F

from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.template import Template, Context

from oscar.test import ClientTestCase
from oscar.test.helpers import create_order
from oscar.apps.order.models import Order, OrderNote
from oscar.apps.dashboard.orders.forms import OrderSearchForm
from oscar.templatetags.dashboard_tags import get_num_user_orders


class OrderSummaryTests(ClientTestCase):
    is_staff = True

    def test_summary_page_has_stats_vars_in_context(self):
        url = reverse('dashboard:order-summary')
        response = self.client.get(url)
        self.assertInContext(response, 'total_orders')
        self.assertInContext(response, 'total_lines')
        self.assertInContext(response, 'total_revenue')


class OrderListTests(ClientTestCase):
    is_staff = True

    def test_searching_for_valid_order_number_redirects_to_order_page(self):
        order = create_order()
        fields = OrderSearchForm.base_fields.keys()
        pairs = dict(zip(fields, ['']*len(fields)))
        pairs['order_number'] = order.number
        pairs['response_format'] = 'html'
        url = '%s?%s' % (reverse('dashboard:order-list'), '&'.join(['%s=%s' % (k,v) for k,v in pairs.items()]))
        response = self.client.get(url)
        self.assertEqual(httplib.FOUND, response.status_code)


class OrderDetailTests(ClientTestCase):
    is_staff = True

    def setUp(self):
        Order.pipeline = {'A': ('B', 'C')}
        self.order = create_order(status='A')
        self.url = reverse('dashboard:order-detail', kwargs={'number': self.order.number})
        super(OrderDetailTests, self).setUp()

    def fetch_order(self):
        return Order.objects.get(number=self.order.number)

    def test_order_detail_page_contains_order(self):
        response = self.client.get(self.url)
        self.assertTrue('order' in response.context)

    def test_order_status_change(self):
        params = {'order_action': 'change_order_status',
                  'new_status': 'B'}
        response = self.client.post(self.url, params)
        self.assertIsRedirect(response)
        self.assertEqual('B', self.fetch_order().status)

    def test_order_status_change_creates_system_note(self):
        params = {'order_action': 'change_order_status',
                  'new_status': 'B'}
        response = self.client.post(self.url, params)
        notes = self.order.notes.all()
        self.assertEqual(1, len(notes))
        self.assertEqual(OrderNote.SYSTEM, notes[0].note_type)


class LineDetailTests(ClientTestCase):
    is_staff = True

    def setUp(self):
        self.order = create_order()
        self.line = self.order.lines.all()[0]
        self.url = reverse('dashboard:order-line-detail', kwargs={'number': self.order.number,
                                                                  'line_id': self.line.id})
        super(LineDetailTests, self).setUp()

    def test_line_detail_page_exists(self):
        response = self.client.get(self.url)
        self.assertIsOk(response)

    def test_line_in_context(self):
        response = self.client.get(self.url)
        self.assertInContext(response, 'line')


class TemplateTagTests(TestCase):
    def test_get_num_orders(self):
        user = get(User)
        for i in range(1, 4):
            get(Order, user=user)
        out = Template(
            "{% load dashboard_tags %}"
            "{% num_orders user %}"
        ).render(Context({
            'user': user
        }))
        self.assertEquals(out, "3")
