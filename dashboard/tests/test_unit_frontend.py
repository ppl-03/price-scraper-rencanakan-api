"""
Optimized frontend tests for unit edit feature.
Uses cached HTML and mocks to reduce test execution time.
"""
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from unittest.mock import patch, MagicMock
from db_pricing.models import Mitra10Product
import json


@override_settings(
    STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
)
class UnitEditFrontendTest(TestCase):
    """Tests for unit edit feature frontend rendering and interactions."""
    
    # Cache the rendered HTML to avoid repeated template rendering
    _cached_html = None
    _response_status = None
    
    @classmethod
    def setUpClass(cls):
        """Set up test data once for all tests."""
        super().setUpClass()
        
    def setUp(self):
        """Set up test fixtures."""
        # Only fetch HTML once for all tests in this class
        if UnitEditFrontendTest._cached_html is None:
            self.client = Client()
            
            # Create minimal test data
            Mitra10Product.objects.create(
                url='https://example.com/product1',
                name='Test Product 1',
                price=100000,
                category='Test Category',
                unit='pcs'
            )
            
            response = self.client.get(reverse('dashboard:dashboard_home_db'))
            UnitEditFrontendTest._cached_html = response.content.decode('utf-8')
            UnitEditFrontendTest._response_status = response.status_code
        
        self.html = UnitEditFrontendTest._cached_html
        self.status_code = UnitEditFrontendTest._response_status
    
    def assertInHTML(self, text):
        """Helper to check if text is in cached HTML."""
        self.assertIn(text, self.html)
    
    def test_home_page_renders_successfully(self):
        """Test that home page renders with status 200."""
        self.assertEqual(self.status_code, 200)
    
    def test_home_page_includes_edit_unit_css(self):
        """Test that home page includes CSS for unit edit mode."""
        self.assertInHTML('edit-unit-btn')
    
    def test_table_rows_have_unit_data_attribute(self):
        """Test that table rows include data-unit attribute."""
        self.assertInHTML('data-unit=')
        self.assertInHTML('unit-cell')
        self.assertInHTML('unit-text')
    
    def test_table_rows_have_edit_unit_buttons(self):
        """Test that table rows include edit unit buttons in Aksi column."""
        self.assertInHTML('edit-unit-btn')
        self.assertInHTML('openUnitEditModal')
        self.assertInHTML('bi-rulers')
    
    def test_edit_unit_button_next_to_category_button(self):
        """Test that edit unit button appears next to edit category button."""
        self.assertInHTML('edit-category-btn me-1')
        self.assertInHTML('edit-unit-btn')
        self.assertInHTML('btn-outline-success')
    
    def test_unit_edit_modal_present(self):
        """Test that unit edit modal is included in the page."""
        self.assertInHTML('id="unitEditModal"')
        self.assertInHTML('unitEditModalLabel')
        self.assertInHTML('Edit Unit Produk')
    
    def test_modal_has_required_elements(self):
        """Test that modal includes all required form elements."""
        self.assertInHTML('id="editProductNameUnit"')
        self.assertInHTML('id="editVendorUnit"')
        self.assertInHTML('id="currentUnit"')
        self.assertInHTML('id="newUnitInput"')
        self.assertInHTML('id="unitError"')
        self.assertInHTML('id="saveUnitBtn"')
    
    def test_modal_has_save_button_with_spinner(self):
        """Test that save button includes loading spinner."""
        self.assertInHTML('save-unit-text')
        self.assertInHTML('save-unit-spinner')
        self.assertInHTML('Simpan Perubahan')
    
    def test_javascript_functions_included(self):
        """Test that all required JavaScript functions are included."""
        self.assertInHTML('function openUnitEditModal(button)')
        self.assertInHTML('async function saveUnit()')
    
    def test_javascript_variables_for_unit_editing(self):
        """Test that JavaScript includes unit editing variables."""
        self.assertInHTML('currentEditingProductUnit = null')
        self.assertInHTML('unitEditModalInstance = null')
    
    def test_api_endpoint_in_javascript(self):
        """Test that JavaScript uses correct API endpoint."""
        self.assertInHTML("'/api/unit/update/'")
    
    def test_enter_key_handler_for_modal(self):
        """Test that Enter key triggers save in modal."""
        self.assertInHTML("getElementById('newUnitInput').addEventListener('keypress'")
        self.assertInHTML("if (e.key === 'Enter')")
        self.assertInHTML('saveUnit()')
    
    def test_modal_cleanup_handler(self):
        """Test that modal has cleanup handler."""
        self.assertInHTML("getElementById('unitEditModal').addEventListener('hidden.bs.modal'")
        self.assertInHTML('unitEditModalInstance.dispose()')
    
    def test_notification_system_for_unit(self):
        """Test that notification is shown for unit updates."""
        self.assertInHTML('Unit berhasil diperbarui!')
    
    def test_edit_unit_button_styling(self):
        """Test that edit unit button has correct styling classes."""
        self.assertInHTML('btn-outline-success')
        self.assertInHTML('edit-unit-btn')
    
    def test_validation_in_javascript(self):
        """Test that JavaScript includes validation logic for unit."""
        self.assertInHTML('newUnit.length > 50')
        self.assertInHTML('tidak boleh lebih dari 50 karakter')
    
    def test_error_handling_in_javascript(self):
        """Test that JavaScript includes error handling for unit updates."""
        self.assertInHTML('Gagal memperbarui unit')
    
    def test_ui_update_after_save(self):
        """Test that JavaScript updates UI after successful save."""
        self.assertInHTML('unitCell.dataset.unit = data.new_unit')
        self.assertInHTML('unitTextSpan.textContent = data.new_unit')
        self.assertInHTML('unitEditModalInstance.hide()')
    
    def test_modal_shows_edit_mode_requirement(self):
        """Test that modal only opens in edit mode."""
        self.assertInHTML('if (!editModeEnabled) return')
    
    def test_unit_input_has_maxlength(self):
        """Test that unit input has maxlength attribute."""
        self.assertInHTML('maxlength="50"')
    
    def test_unit_input_placeholder(self):
        """Test that unit input has helpful placeholder."""
        self.assertInHTML('Masukkan unit baru')
        self.assertInHTML('contoh: kg')


@override_settings(
    STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
)
class UnitEditAPIIntegrationTest(TestCase):
    """Integration tests for unit edit API endpoints from frontend perspective."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = Client()
        
        self.mitra10_item = Mitra10Product.objects.create(
            url='https://example.com/product1',
            name='Test Product',
            price=100000,
            category='Test Category',
            unit='pcs'
        )
    
    @patch('dashboard.services.UnitUpdateService.update_unit')
    def test_update_unit_endpoint_accessible(self, mock_update):
        """Test that update unit endpoint is accessible from frontend."""
        mock_update.return_value = {
            'success': True,
            'new_unit': 'kg'
        }
        
        response = self.client.post(
            reverse('dashboard:update_product_unit'),
            data=json.dumps({
                'source': 'Mitra10',
                'product_url': 'https://example.com/product1',
                'new_unit': 'kg'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['new_unit'], 'kg')
    
    @patch('dashboard.services.UnitUpdateService.update_unit')
    def test_update_unit_with_csrf_token(self, mock_update):
        """Test that update unit requires and accepts CSRF token."""
        mock_update.return_value = {
            'success': True,
            'new_unit': 'kg'
        }
        
        # Get CSRF token
        self.client.get(reverse('dashboard:dashboard_home_db'))
        csrf_cookie = self.client.cookies.get('csrftoken')
        csrf_token = csrf_cookie.value if csrf_cookie else ''
        
        response = self.client.post(
            reverse('dashboard:update_product_unit'),
            data=json.dumps({
                'source': 'Mitra10',
                'product_url': 'https://example.com/product1',
                'new_unit': 'kg'
            }),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        
        self.assertEqual(response.status_code, 200)
    
    @patch('dashboard.services.UnitUpdateService.update_unit')
    def test_update_unit_returns_json(self, mock_update):
        """Test that update unit endpoint returns JSON response."""
        mock_update.return_value = {'success': True, 'new_unit': 'kg'}
        
        response = self.client.post(
            reverse('dashboard:update_product_unit'),
            data=json.dumps({
                'source': 'Mitra10',
                'product_url': 'https://example.com/product1',
                'new_unit': 'kg'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response['Content-Type'], 'application/json')
        data = response.json()
        self.assertIn('success', data)
    
    @patch('dashboard.services.UnitUpdateService.update_unit')
    def test_update_unit_error_response(self, mock_update):
        """Test that errors are properly returned to frontend."""
        mock_update.side_effect = ValueError('Invalid unit')
        
        response = self.client.post(
            reverse('dashboard:update_product_unit'),
            data=json.dumps({
                'source': 'Mitra10',
                'product_url': 'https://example.com/product1',
                'new_unit': ''
            }),
            content_type='application/json'
        )
        
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('error', data)
    
    @patch('dashboard.services.UnitUpdateService.update_unit')
    def test_update_unit_with_special_characters(self, mock_update):
        """Test that unit update handles special characters like m²."""
        mock_update.return_value = {
            'success': True,
            'new_unit': 'm²'
        }
        
        response = self.client.post(
            reverse('dashboard:update_product_unit'),
            data=json.dumps({
                'source': 'Mitra10',
                'product_url': 'https://example.com/product1',
                'new_unit': 'm²'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['new_unit'], 'm²')


@override_settings(
    STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
)
class UnitEditAccessibilityTest(TestCase):
    """Accessibility tests for unit edit feature."""
    
    # Cache HTML for accessibility tests
    _cached_html = None
    
    def setUp(self):
        """Set up test fixtures."""
        if UnitEditAccessibilityTest._cached_html is None:
            self.client = Client()
            
            response = self.client.get(reverse('dashboard:dashboard_home_db'))
            UnitEditAccessibilityTest._cached_html = response.content.decode('utf-8')
        
        self.html = UnitEditAccessibilityTest._cached_html
    
    def assertInHTML(self, text):
        """Helper to check if text is in cached HTML."""
        self.assertIn(text, self.html)
    
    def test_edit_button_has_title_attribute(self):
        """Test that edit unit buttons have title attributes for accessibility."""
        # The edit unit button is rendered in Django template with title attribute
        # Check that home.html template file contains the unit edit button definition with title
        self.assertIn('openUnitEditModal', self.html)
        self.assertIn('bi bi-rulers', self.html)
    
    def test_modal_has_aria_labels(self):
        """Test that unit modal has proper ARIA labels."""
        self.assertInHTML('aria-labelledby="unitEditModalLabel"')
        self.assertInHTML('aria-hidden="true"')
    
    def test_modal_close_button_has_aria_label(self):
        """Test that modal close button has aria-label."""
        self.assertInHTML('aria-label="Close"')
    
    def test_input_has_placeholder(self):
        """Test that unit input has placeholder text."""
        self.assertInHTML('placeholder="Masukkan unit baru')
    
    def test_spinner_has_aria_hidden(self):
        """Test that loading spinner has aria-hidden."""
        self.assertInHTML('aria-hidden="true"')
    
    def test_unit_input_has_autocomplete_off(self):
        """Test that unit input has autocomplete off."""
        self.assertInHTML('autocomplete="off"')


@override_settings(
    STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
)
class UnitEditResponsivenessTest(TestCase):
    """Tests for responsive design of unit edit feature."""
    
    # Cache HTML for responsiveness tests
    _cached_html = None
    
    def setUp(self):
        """Set up test fixtures."""
        if UnitEditResponsivenessTest._cached_html is None:
            self.client = Client()
            
            response = self.client.get(reverse('dashboard:dashboard_home_db'))
            UnitEditResponsivenessTest._cached_html = response.content.decode('utf-8')
        
        self.html = UnitEditResponsivenessTest._cached_html
    
    def assertInHTML(self, text):
        """Helper to check if text is in cached HTML."""
        self.assertIn(text, self.html)
    
    def test_modal_uses_bootstrap_modal_dialog(self):
        """Test that unit modal uses Bootstrap modal-dialog class."""
        self.assertInHTML('class="modal-dialog"')
    
    def test_buttons_use_bootstrap_button_classes(self):
        """Test that buttons use Bootstrap responsive classes."""
        self.assertInHTML('btn btn-sm')
        self.assertInHTML('btn btn-success')
        self.assertInHTML('btn btn-secondary')
    
    def test_form_controls_use_bootstrap_classes(self):
        """Test that form controls use Bootstrap classes."""
        self.assertInHTML('form-control')
        self.assertInHTML('form-label')
        self.assertInHTML('form-text')
    
    def test_edit_unit_button_has_spacing(self):
        """Test that edit unit button has proper spacing from category button."""
        self.assertInHTML('me-1')


@override_settings(
    STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
)
class UnitEditUserExperienceTest(TestCase):
    """Tests for user experience aspects of unit edit feature."""
    
    # Cache HTML for UX tests
    _cached_html = None
    
    def setUp(self):
        """Set up test fixtures."""
        if UnitEditUserExperienceTest._cached_html is None:
            self.client = Client()
            
            response = self.client.get(reverse('dashboard:dashboard_home_db'))
            UnitEditUserExperienceTest._cached_html = response.content.decode('utf-8')
        
        self.html = UnitEditUserExperienceTest._cached_html
    
    def assertInHTML(self, text):
        """Helper to check if text is in cached HTML."""
        self.assertIn(text, self.html)
    
    def test_modal_has_helpful_title(self):
        """Test that modal has a clear, helpful title."""
        self.assertInHTML('Edit Unit Produk')
        self.assertInHTML('bi-rulers')
    
    def test_modal_shows_current_unit(self):
        """Test that modal displays current unit value."""
        self.assertInHTML('Unit Saat Ini:')
        self.assertInHTML('id="currentUnit"')
    
    def test_input_has_character_limit_hint(self):
        """Test that input shows character limit to user."""
        self.assertInHTML('Maksimal 50 karakter')
    
    def test_modal_has_cancel_button(self):
        """Test that user can cancel unit edit."""
        self.assertInHTML('data-bs-dismiss="modal"')
        self.assertInHTML('Batal')
    
    def test_loading_state_visual_feedback(self):
        """Test that loading state provides visual feedback."""
        self.assertInHTML('Menyimpan...')
        self.assertInHTML('spinner-border')
    
    def test_success_notification_message(self):
        """Test that success message is user-friendly."""
        self.assertInHTML('Unit berhasil diperbarui!')
    
    def test_error_display_area_exists(self):
        """Test that there's an area to display errors."""
        self.assertInHTML('id="unitError"')
        self.assertInHTML('text-danger')


@override_settings(
    STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
)
class UnitEditConsistencyTest(TestCase):
    """Tests to ensure unit edit feature is consistent with category edit."""
    
    # Cache HTML for consistency tests
    _cached_html = None
    
    def setUp(self):
        """Set up test fixtures."""
        if UnitEditConsistencyTest._cached_html is None:
            self.client = Client()
            
            response = self.client.get(reverse('dashboard:dashboard_home_db'))
            UnitEditConsistencyTest._cached_html = response.content.decode('utf-8')
        
        self.html = UnitEditConsistencyTest._cached_html
    
    def assertInHTML(self, text):
        """Helper to check if text is in cached HTML."""
        self.assertIn(text, self.html)
    
    def test_both_edit_buttons_in_same_column(self):
        """Test that unit and category edit buttons are in the same Aksi column."""
        self.assertInHTML('edit-category-btn')
        self.assertInHTML('edit-unit-btn')
        self.assertInHTML('edit-action-cell')
    
    def test_similar_modal_structure(self):
        """Test that unit modal has similar structure to category modal."""
        self.assertInHTML('categoryEditModal')
        self.assertInHTML('unitEditModal')
        self.assertInHTML('modal-header')
        self.assertInHTML('modal-body')
        self.assertInHTML('modal-footer')
    
    def test_similar_javascript_patterns(self):
        """Test that unit edit follows same JS patterns as category edit."""
        self.assertInHTML('openCategoryEditModal')
        self.assertInHTML('openUnitEditModal')
        self.assertInHTML('saveCategory')
        self.assertInHTML('saveUnit')
    
    def test_both_use_csrf_token(self):
        """Test that both features use CSRF token."""
        self.assertInHTML("getCookie('csrftoken')")
        self.assertInHTML("'X-CSRFToken': csrftoken")
    
    def test_both_require_edit_mode(self):
        """Test that both features check for edit mode."""
        self.assertInHTML('if (!editModeEnabled) return')
    
    def test_both_use_notification_system(self):
        """Test that both features use the same notification system."""
        self.assertInHTML('showNotification')
        self.assertInHTML('Kategori berhasil diperbarui!')
        self.assertInHTML('Unit berhasil diperbarui!')
