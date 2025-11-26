"""
Optimized frontend tests for category edit feature.
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
class CategoryEditFrontendTest(TestCase):
    """Tests for category edit feature frontend rendering and interactions."""
    
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
        if CategoryEditFrontendTest._cached_html is None:
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
            CategoryEditFrontendTest._cached_html = response.content.decode('utf-8')
            CategoryEditFrontendTest._response_status = response.status_code
        
        self.html = CategoryEditFrontendTest._cached_html
        self.status_code = CategoryEditFrontendTest._response_status
    
    def assertInHTML(self, text):
        """Helper to check if text is in cached HTML."""
        self.assertIn(text, self.html)
    
    def test_home_page_renders_edit_mode_button(self):
        """Test that home page includes edit mode toggle button."""
        self.assertEqual(self.status_code, 200)
        self.assertInHTML('id="editModeToggle"')
        self.assertInHTML('Enable Edit Mode')
        self.assertInHTML('bi-pencil-square')
    
    def test_home_page_includes_edit_mode_css(self):
        """Test that home page includes CSS for edit mode."""
        self.assertInHTML('Edit Mode Styles')
        self.assertInHTML('edit-mode-header')
        self.assertInHTML('edit-action-cell')
        self.assertInHTML('edit-category-btn')
    
    def test_table_has_aksi_column_header(self):
        """Test that table includes Aksi column header."""
        self.assertInHTML('edit-mode-header')
        self.assertInHTML('>Aksi<')
    
    def test_table_rows_have_edit_buttons(self):
        """Test that table rows include edit buttons in Aksi column."""
        self.assertInHTML('edit-action-cell')
        self.assertInHTML('edit-category-btn')
        self.assertInHTML('openCategoryEditModal')
        self.assertInHTML('bi-pencil')
    
    def test_table_rows_have_data_attributes(self):
        """Test that table rows include required data attributes."""
        self.assertInHTML('data-product-url=')
        self.assertInHTML('data-vendor=')
        self.assertInHTML('data-category=')
    
    def test_category_edit_modal_present(self):
        """Test that category edit modal is included in the page."""
        self.assertInHTML('id="categoryEditModal"')
        self.assertInHTML('categoryEditModalLabel')
        self.assertInHTML('Edit Kategori Produk')
    
    def test_modal_has_required_elements(self):
        """Test that modal includes all required form elements."""
        self.assertInHTML('id="editProductName"')
        self.assertInHTML('id="editVendor"')
        self.assertInHTML('id="currentCategory"')
        self.assertInHTML('id="newCategoryInput"')
        self.assertInHTML('id="categoryError"')
        self.assertInHTML('id="saveCategoryBtn"')
    
    def test_modal_has_save_button_with_spinner(self):
        """Test that save button includes loading spinner."""
        self.assertInHTML('save-text')
        self.assertInHTML('save-spinner')
        self.assertInHTML('Simpan Perubahan')
    
    def test_javascript_functions_included(self):
        """Test that all required JavaScript functions are included."""
        self.assertInHTML('function getCookie(name)')
        self.assertInHTML('function openCategoryEditModal(button)')
        self.assertInHTML('async function saveCategory()')
        self.assertInHTML('function showNotification(message, type')
    
    def test_edit_mode_toggle_event_listener(self):
        """Test that edit mode toggle has event listener."""
        self.assertInHTML("getElementById('editModeToggle').addEventListener('click'")
        self.assertInHTML('editModeEnabled = !editModeEnabled')
    
    def test_csrf_token_handling_in_javascript(self):
        """Test that JavaScript includes CSRF token handling."""
        self.assertInHTML("getCookie('csrftoken')")
        self.assertInHTML("'X-CSRFToken': csrftoken")
    
    def test_api_endpoint_in_javascript(self):
        """Test that JavaScript uses correct API endpoint."""
        self.assertInHTML("'/api/category/update/'")
    
    def test_enter_key_handler_for_modal(self):
        """Test that Enter key triggers save in modal."""
        self.assertInHTML("getElementById('newCategoryInput').addEventListener('keypress'")
        self.assertInHTML("if (e.key === 'Enter')")
        self.assertInHTML('saveCategory()')
    
    def test_modal_cleanup_handler(self):
        """Test that modal has cleanup handler."""
        self.assertInHTML("getElementById('categoryEditModal').addEventListener('hidden.bs.modal'")
        self.assertInHTML('categoryEditModalInstance.dispose()')
    
    def test_notification_system_included(self):
        """Test that notification system is included."""
        self.assertInHTML('showNotification')
        self.assertInHTML('alert-dismissible')
        self.assertInHTML('Kategori berhasil diperbarui!')
    
    def test_edit_mode_button_styling(self):
        """Test that edit mode button has correct styling classes."""
        self.assertInHTML('btn-outline-secondary')
        self.assertInHTML('edit-mode-btn')
        self.assertInHTML('btn-success')
    
    def test_validation_in_javascript(self):
        """Test that JavaScript includes validation logic."""
        self.assertInHTML('newCategory.length > 100')
        self.assertInHTML('tidak boleh lebih dari 100 karakter')
    
    def test_error_handling_in_javascript(self):
        """Test that JavaScript includes error handling."""
        self.assertInHTML('catch (error)')
        self.assertInHTML('Terjadi kesalahan jaringan')
        self.assertInHTML('Gagal memperbarui kategori')
    
    def test_ui_update_after_save(self):
        """Test that JavaScript updates UI after successful save."""
        self.assertInHTML('categoryCell.dataset.category = data.new_category')
        self.assertInHTML('categoryTextSpan.textContent = data.new_category')
        self.assertInHTML('categoryEditModalInstance.hide()')


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
class CategoryEditAPIIntegrationTest(TestCase):
    """Integration tests for category edit API endpoints from frontend perspective."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = Client()
        
        self.mitra10_item = Mitra10Product.objects.create(
            url='https://example.com/product1',
            name='Test Product',
            price=100000,
            category='Old Category',
            unit='pcs'
        )
    
    @patch('dashboard.services.CategoryUpdateService.update_category')
    def test_update_category_endpoint_accessible(self, mock_update):
        """Test that update category endpoint is accessible from frontend."""
        mock_update.return_value = {
            'success': True,
            'new_category': 'New Category'
        }
        
        response = self.client.post(
            reverse('dashboard:update_product_category'),
            data=json.dumps({
                'source': 'Mitra10',
                'product_url': 'https://example.com/product1',
                'new_category': 'New Category'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['new_category'], 'New Category')
    
    @patch('dashboard.services.CategoryUpdateService.update_category')
    def test_update_category_with_csrf_token(self, mock_update):
        """Test that update category requires and accepts CSRF token."""
        mock_update.return_value = {
            'success': True,
            'new_category': 'New Category'
        }
        
        # Get CSRF token
        self.client.get(reverse('dashboard:dashboard_home_db'))
        csrf_cookie = self.client.cookies.get('csrftoken')
        csrf_token = csrf_cookie.value if csrf_cookie else ''
        
        response = self.client.post(
            reverse('dashboard:update_product_category'),
            data=json.dumps({
                'source': 'Mitra10',
                'product_url': 'https://example.com/product1',
                'new_category': 'New Category'
            }),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        
        self.assertEqual(response.status_code, 200)
    
    @patch('dashboard.services.CategoryUpdateService.update_category')
    def test_update_category_returns_json(self, mock_update):
        """Test that update category endpoint returns JSON response."""
        mock_update.return_value = {'success': True, 'new_category': 'New Category'}
        
        response = self.client.post(
            reverse('dashboard:update_product_category'),
            data=json.dumps({
                'source': 'Mitra10',
                'product_url': 'https://example.com/product1',
                'new_category': 'New Category'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response['Content-Type'], 'application/json')
        data = response.json()
        self.assertIn('success', data)
    
    @patch('dashboard.services.CategoryUpdateService.update_category')
    def test_update_category_error_response(self, mock_update):
        """Test that errors are properly returned to frontend."""
        mock_update.side_effect = ValueError('Invalid category')
        
        response = self.client.post(
            reverse('dashboard:update_product_category'),
            data=json.dumps({
                'source': 'Mitra10',
                'product_url': 'https://example.com/product1',
                'new_category': ''
            }),
            content_type='application/json'
        )
        
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('error', data)


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
class CategoryEditAccessibilityTest(TestCase):
    """Accessibility tests for category edit feature."""
    
    # Cache HTML for accessibility tests
    _cached_html = None
    
    def setUp(self):
        """Set up test fixtures."""
        if CategoryEditAccessibilityTest._cached_html is None:
            self.client = Client()
            
            response = self.client.get(reverse('dashboard:dashboard_home_db'))
            CategoryEditAccessibilityTest._cached_html = response.content.decode('utf-8')
        
        self.html = CategoryEditAccessibilityTest._cached_html
    
    def assertInHTML(self, text):
        """Helper to check if text is in cached HTML."""
        self.assertIn(text, self.html)
    
    def test_edit_button_has_title_attribute(self):
        """Test that edit buttons have title attributes for accessibility."""
        self.assertInHTML('title="Edit Category"')
    
    def test_modal_has_aria_labels(self):
        """Test that modal has proper ARIA labels."""
        self.assertInHTML('aria-labelledby="categoryEditModalLabel"')
        self.assertInHTML('aria-hidden="true"')
    
    def test_modal_close_button_has_aria_label(self):
        """Test that modal close button has aria-label."""
        self.assertInHTML('aria-label="Close"')
    
    def test_input_has_placeholder(self):
        """Test that category input has placeholder text."""
        self.assertInHTML('placeholder="Masukkan kategori baru..."')
    
    def test_spinner_has_aria_hidden(self):
        """Test that loading spinner has aria-hidden."""
        self.assertInHTML('aria-hidden="true"')


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
class CategoryEditResponsivenessTest(TestCase):
    """Tests for responsive design of category edit feature."""
    
    # Cache HTML for responsiveness tests
    _cached_html = None
    
    def setUp(self):
        """Set up test fixtures."""
        if CategoryEditResponsivenessTest._cached_html is None:
            self.client = Client()
            
            response = self.client.get(reverse('dashboard:dashboard_home_db'))
            CategoryEditResponsivenessTest._cached_html = response.content.decode('utf-8')
        
        self.html = CategoryEditResponsivenessTest._cached_html
    
    def assertInHTML(self, text):
        """Helper to check if text is in cached HTML."""
        self.assertIn(text, self.html)
    
    def test_modal_uses_bootstrap_modal_dialog(self):
        """Test that modal uses Bootstrap modal-dialog class."""
        self.assertInHTML('class="modal-dialog"')
    
    def test_buttons_use_bootstrap_button_classes(self):
        """Test that buttons use Bootstrap responsive classes."""
        self.assertInHTML('btn btn-sm')
        self.assertInHTML('btn btn-primary')
        self.assertInHTML('btn btn-secondary')
    
    def test_form_controls_use_bootstrap_classes(self):
        """Test that form controls use Bootstrap classes."""
        self.assertInHTML('form-control')
        self.assertInHTML('form-label')
        self.assertInHTML('form-text')
