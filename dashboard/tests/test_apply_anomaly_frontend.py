"""
Test suite for Frontend Apply Anomaly UI Components
Tests that the price_anomalies.html template includes the correct buttons,
CSS classes, and JavaScript functions for applying anomalies
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.test.utils import override_settings
from unittest.mock import patch
import re


@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class ApplyAnomalyFrontendUITestCase(TestCase):
    """Test frontend UI elements for apply anomaly functionality"""

    def setUp(self):
        self.client = Client()
        self._patcher = patch(
            'django.contrib.staticfiles.storage.staticfiles_storage.url',
            return_value='/static/dashboard/images/rencanakan_logo.png'
        )
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()

    def test_page_renders_successfully(self):
        """Test that the price anomalies page renders without errors"""
        url = reverse('dashboard:price_anomalies')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/price_anomalies.html')

    def test_apply_button_css_exists(self):
        """Test that btn-apply CSS class is defined in the template"""
        url = reverse('dashboard:price_anomalies')
        response = self.client.get(url)
        content = response.content.decode('utf-8')
        
        # Check for btn-apply CSS definition
        self.assertIn('.btn-apply', content)
        self.assertIn('background-color: #28a745', content)

    def test_approve_and_apply_button_css_exists(self):
        """Test that btn-approve-apply CSS class is defined in the template"""
        url = reverse('dashboard:price_anomalies')
        response = self.client.get(url)
        content = response.content.decode('utf-8')
        
        # Check for btn-approve-apply CSS definition
        self.assertIn('.btn-approve-apply', content)
        self.assertIn('background-color: #17a2b8', content)

    def test_applied_badge_css_exists(self):
        """Test that badge-applied CSS class is defined in the template"""
        url = reverse('dashboard:price_anomalies')
        response = self.client.get(url)
        content = response.content.decode('utf-8')
        
        # Check for badge-applied CSS definition
        self.assertIn('.badge-applied', content)
        self.assertIn('background-color: #d1ecf1', content)
        self.assertIn('color: #0c5460', content)

    def test_apply_anomaly_javascript_function_exists(self):
        """Test that applyAnomaly JavaScript function is defined"""
        url = reverse('dashboard:price_anomalies')
        response = self.client.get(url)
        content = response.content.decode('utf-8')
        
        # Check for function definition
        self.assertIn('function applyAnomaly(anomalyId)', content)
        
        # Check for API endpoint call
        self.assertIn('/api/pricing/anomalies/${anomalyId}/apply/', content)
        
        # Check for confirmation dialog
        pattern = re.compile(r'confirm.*apply.*price.*change', re.IGNORECASE)
        self.assertTrue(pattern.search(content), "Apply confirmation dialog not found")

    def test_approve_and_apply_javascript_function_exists(self):
        """Test that approveAndApply JavaScript function is defined"""
        url = reverse('dashboard:price_anomalies')
        response = self.client.get(url)
        content = response.content.decode('utf-8')
        
        # Check for function definition
        self.assertIn('function approveAndApply(anomalyId)', content)
        
        # Check for API endpoint call
        self.assertIn('/api/pricing/anomalies/${anomalyId}/approve-and-apply/', content)
        
        # Check for confirmation dialog
        pattern = re.compile(r'confirm.*approve.*immediately.*apply', re.IGNORECASE)
        self.assertTrue(pattern.search(content), "Approve-and-apply confirmation dialog not found")

    def test_javascript_functions_include_csrf_token(self):
        """Test that JavaScript functions include CSRF token in headers"""
        url = reverse('dashboard:price_anomalies')
        response = self.client.get(url)
        content = response.content.decode('utf-8')
        
        # Extract applyAnomaly function
        apply_match = re.search(r'function applyAnomaly\(.*?\)\s*{(.*?)}(?=\s*function)', content, re.DOTALL)
        self.assertIsNotNone(apply_match, "applyAnomaly function not found")
        apply_function = apply_match.group(1)
        
        # Check for CSRF token
        self.assertIn("'X-CSRFToken': getCookie('csrftoken')", apply_function)
        
        # Extract approveAndApply function
        approve_apply_match = re.search(r'function approveAndApply\(.*?\)\s*{(.*?)}(?=\s*function)', content, re.DOTALL)
        self.assertIsNotNone(approve_apply_match, "approveAndApply function not found")
        approve_apply_function = approve_apply_match.group(1)
        
        # Check for CSRF token
        self.assertIn("'X-CSRFToken': getCookie('csrftoken')", approve_apply_function)

    def test_javascript_functions_handle_success(self):
        """Test that JavaScript functions handle success responses"""
        url = reverse('dashboard:price_anomalies')
        response = self.client.get(url)
        content = response.content.decode('utf-8')
        
        # Check applyAnomaly success handling
        apply_match = re.search(r'function applyAnomaly\(.*?\)\s*{(.*?)}(?=\s*function)', content, re.DOTALL)
        apply_function = apply_match.group(1)
        self.assertIn('loadAnomalies(currentPage)', apply_function)
        self.assertIn('loadStatistics()', apply_function)
        
        # Check approveAndApply success handling
        approve_apply_match = re.search(r'function approveAndApply\(.*?\)\s*{(.*?)}(?=\s*function)', content, re.DOTALL)
        approve_apply_function = approve_apply_match.group(1)
        self.assertIn('loadAnomalies(currentPage)', approve_apply_function)
        self.assertIn('loadStatistics()', approve_apply_function)

    def test_javascript_functions_handle_errors(self):
        """Test that JavaScript functions handle error responses"""
        url = reverse('dashboard:price_anomalies')
        response = self.client.get(url)
        content = response.content.decode('utf-8')
        
        # Check applyAnomaly error handling
        apply_match = re.search(r'function applyAnomaly\(.*?\)\s*{(.*?)}(?=\s*function)', content, re.DOTALL)
        apply_function = apply_match.group(1)
        self.assertIn('.catch(error =>', apply_function)
        self.assertIn('alert', apply_function)
        
        # Check approveAndApply error handling
        approve_apply_match = re.search(r'function approveAndApply\(.*?\)\s*{(.*?)}(?=\s*function)', content, re.DOTALL)
        approve_apply_function = approve_apply_match.group(1)
        self.assertIn('.catch(error =>', approve_apply_function)
        self.assertIn('alert', approve_apply_function)

    def test_format_status_includes_applied(self):
        """Test that formatStatus function includes 'applied' status"""
        url = reverse('dashboard:price_anomalies')
        response = self.client.get(url)
        content = response.content.decode('utf-8')
        
        # Find formatStatus function
        format_status_match = re.search(r'function formatStatus\(.*?\)\s*{(.*?)}', content, re.DOTALL)
        self.assertIsNotNone(format_status_match, "formatStatus function not found")
        format_status_function = format_status_match.group(1)
        
        # Check for 'applied' status mapping
        self.assertIn("'applied'", format_status_function)
        self.assertIn("'Applied'", format_status_function)

    def test_apply_button_shown_for_approved_status(self):
        """Test that Apply button appears for approved anomalies"""
        url = reverse('dashboard:price_anomalies')
        response = self.client.get(url)
        content = response.content.decode('utf-8')
        
        # Look for conditional rendering of Apply button
        pattern = re.compile(r"anomaly\.status\s*===\s*['\"]approved['\"].*?btn-apply.*?Apply\s+Price", re.DOTALL | re.IGNORECASE)
        self.assertTrue(pattern.search(content), "Apply button for approved status not found")

    def test_approve_and_apply_button_shown_for_pending_status(self):
        """Test that Approve & Apply button appears for pending anomalies"""
        url = reverse('dashboard:price_anomalies')
        response = self.client.get(url)
        content = response.content.decode('utf-8')
        
        # Look for conditional rendering of Approve & Apply button
        pattern = re.compile(r"anomaly\.status\s*===\s*['\"]pending['\"].*?btn-approve-apply.*?Approve\s+&\s+Apply", re.DOTALL | re.IGNORECASE)
        self.assertTrue(pattern.search(content), "Approve & Apply button for pending status not found")

    def test_apply_button_calls_apply_anomaly_function(self):
        """Test that Apply button calls applyAnomaly function with correct parameter"""
        url = reverse('dashboard:price_anomalies')
        response = self.client.get(url)
        content = response.content.decode('utf-8')
        
        # Check for onclick handler
        pattern = re.compile(r'btn-apply.*?onclick=["\']applyAnomaly\(\$\{anomaly\.id\}\)', re.DOTALL)
        self.assertTrue(pattern.search(content), "Apply button onclick handler not found")

    def test_approve_and_apply_button_calls_approve_and_apply_function(self):
        """Test that Approve & Apply button calls approveAndApply function with correct parameter"""
        url = reverse('dashboard:price_anomalies')
        response = self.client.get(url)
        content = response.content.decode('utf-8')
        
        # Check for onclick handler
        pattern = re.compile(r'btn-approve-apply.*?onclick=["\']approveAndApply\(\$\{anomaly\.id\}\)', re.DOTALL)
        self.assertTrue(pattern.search(content), "Approve & Apply button onclick handler not found")

    def test_apply_button_has_correct_icon(self):
        """Test that Apply button has check-circle icon"""
        url = reverse('dashboard:price_anomalies')
        response = self.client.get(url)
        content = response.content.decode('utf-8')
        
        # Look for icon in Apply button
        pattern = re.compile(r'btn-apply.*?<i\s+class=["\'].*?fa-check-circle.*?["\'].*?Apply\s+Price', re.DOTALL | re.IGNORECASE)
        self.assertTrue(pattern.search(content), "Apply button icon not found")

    def test_approve_and_apply_button_has_correct_icon(self):
        """Test that Approve & Apply button has bolt icon"""
        url = reverse('dashboard:price_anomalies')
        response = self.client.get(url)
        content = response.content.decode('utf-8')
        
        # Look for icon in Approve & Apply button
        pattern = re.compile(r'btn-approve-apply.*?<i\s+class=["\'].*?fa-bolt.*?["\'].*?Approve\s+&\s+Apply', re.DOTALL | re.IGNORECASE)
        self.assertTrue(pattern.search(content), "Approve & Apply button icon not found")

    def test_reviewed_status_shows_approve_and_reject_buttons(self):
        """Test that reviewed status shows Approve and Reject buttons"""
        url = reverse('dashboard:price_anomalies')
        response = self.client.get(url)
        content = response.content.decode('utf-8')
        
        # Look for conditional rendering for reviewed status
        pattern = re.compile(r"anomaly\.status\s*===\s*['\"]reviewed['\"].*?btn-approve.*?Approve", re.DOTALL | re.IGNORECASE)
        self.assertTrue(pattern.search(content), "Approve button for reviewed status not found")
        
        pattern = re.compile(r"anomaly\.status\s*===\s*['\"]reviewed['\"].*?btn-reject.*?Reject", re.DOTALL | re.IGNORECASE)
        self.assertTrue(pattern.search(content), "Reject button for reviewed status not found")


@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class ApplyAnomalyButtonVisibilityTestCase(TestCase):
    """Test button visibility logic for different anomaly statuses"""

    def setUp(self):
        self.client = Client()
        self._patcher = patch(
            'django.contrib.staticfiles.storage.staticfiles_storage.url',
            return_value='/static/dashboard/images/rencanakan_logo.png'
        )
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()

    def test_pending_status_buttons(self):
        """Test that pending status shows correct buttons"""
        url = reverse('dashboard:price_anomalies')
        response = self.client.get(url)
        content = response.content.decode('utf-8')
        
        # Find the pending status condition block
        pending_block_match = re.search(
            r"anomaly\.status\s*===\s*['\"]pending['\"].*?\?.*?`(.*?)`\s*:",
            content,
            re.DOTALL
        )
        self.assertIsNotNone(pending_block_match, "Pending status condition not found")
        pending_block = pending_block_match.group(1)
        
        # Check for all expected buttons
        self.assertIn('btn-approve', pending_block)
        self.assertIn('Approve', pending_block)
        self.assertIn('btn-reject', pending_block)
        self.assertIn('Reject', pending_block)
        self.assertIn('btn-approve-apply', pending_block)
        self.assertIn('Approve & Apply', pending_block)
        self.assertIn('btn-review', pending_block)
        self.assertIn('Review', pending_block)

    def test_approved_status_buttons(self):
        """Test that approved status shows Apply, Reject, and Edit Notes buttons"""
        url = reverse('dashboard:price_anomalies')
        response = self.client.get(url)
        content = response.content.decode('utf-8')
        
        # Look for approved status condition
        approved_pattern = re.compile(
            r"anomaly\.status\s*===\s*['\"]approved['\"].*?\?.*?`(.*?)`",
            re.DOTALL
        )
        approved_match = approved_pattern.search(content)
        self.assertIsNotNone(approved_match, "Approved status condition not found")
        approved_block = approved_match.group(1)
        
        # Check for expected buttons
        self.assertIn('btn-apply', approved_block)
        self.assertIn('Apply Price', approved_block)
        self.assertIn('btn-reject', approved_block)
        self.assertIn('Reject', approved_block)
        self.assertIn('btn-review', approved_block)
        self.assertIn('Edit Notes', approved_block)

    def test_css_button_colors_are_distinct(self):
        """Test that different button types have distinct colors"""
        url = reverse('dashboard:price_anomalies')
        response = self.client.get(url)
        content = response.content.decode('utf-8')
        
        # Extract button colors
        approve_color_match = re.search(r'\.btn-approve\s*{[^}]*background-color:\s*([^;]+)', content)
        reject_color_match = re.search(r'\.btn-reject\s*{[^}]*background-color:\s*([^;]+)', content)
        apply_color_match = re.search(r'\.btn-apply\s*{[^}]*background-color:\s*([^;]+)', content)
        approve_apply_color_match = re.search(r'\.btn-approve-apply\s*{[^}]*background-color:\s*([^;]+)', content)
        
        self.assertIsNotNone(approve_color_match, "btn-approve color not found")
        self.assertIsNotNone(reject_color_match, "btn-reject color not found")
        self.assertIsNotNone(apply_color_match, "btn-apply color not found")
        self.assertIsNotNone(approve_apply_color_match, "btn-approve-apply color not found")
        
        # All colors should be different
        colors = [
            approve_color_match.group(1).strip(),
            reject_color_match.group(1).strip(),
            apply_color_match.group(1).strip(),
            approve_apply_color_match.group(1).strip()
        ]
        self.assertEqual(len(colors), len(set(colors)), "Button colors are not distinct")

    def test_all_status_badges_have_unique_colors(self):
        """Test that all status badges have unique colors"""
        url = reverse('dashboard:price_anomalies')
        response = self.client.get(url)
        content = response.content.decode('utf-8')
        
        # Extract badge colors
        badge_classes = ['badge-pending', 'badge-reviewed', 'badge-approved', 'badge-rejected', 'badge-applied']
        badge_colors = {}
        
        for badge_class in badge_classes:
            color_match = re.search(rf'\.{badge_class}\s*{{[^}}]*background-color:\s*([^;]+)', content)
            self.assertIsNotNone(color_match, f"{badge_class} color not found")
            badge_colors[badge_class] = color_match.group(1).strip()
        
        # All badge colors should be unique
        unique_colors = set(badge_colors.values())
        self.assertEqual(len(unique_colors), len(badge_classes), 
                        f"Badge colors are not unique: {badge_colors}")
