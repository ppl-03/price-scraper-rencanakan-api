"""
Tests for the api_token_required decorator in the gemilang module.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from django.http import JsonResponse
from api.gemilang.decorators import api_token_required


class TestApiTokenRequiredDecorator:
    """Test cases for the api_token_required decorator."""

    def test_decorator_with_valid_token(self):
        """Test that the decorator allows access when token is valid."""
        # Create a mock view function
        mock_view = Mock(return_value=JsonResponse({'status': 'success'}, status=200))
        
        # Apply the decorator
        decorated_view = api_token_required(mock_view)
        
        # Create a mock request
        mock_request = Mock()
        
        # Mock _validate_api_token to return success
        with patch('api.gemilang.decorators.logger') as mock_logger:
            with patch('api.gemilang.views._validate_api_token', return_value=(True, None)):
                # Call the decorated view
                response = decorated_view(mock_request)
                
                # Assert the view function was called
                mock_view.assert_called_once_with(mock_request)
                
                # Assert logger.warning was not called
                mock_logger.warning.assert_not_called()
                
                # Assert response is from the view
                assert response.status_code == 200

    def test_decorator_with_invalid_token(self):
        """Test that the decorator blocks access when token is invalid."""
        # Create a mock view function
        mock_view = Mock(return_value=JsonResponse({'status': 'success'}, status=200))
        
        # Apply the decorator
        decorated_view = api_token_required(mock_view)
        
        # Create a mock request
        mock_request = Mock()
        
        # Mock _validate_api_token to return failure
        with patch('api.gemilang.decorators.logger') as mock_logger:
            with patch('api.gemilang.views._validate_api_token', return_value=(False, 'Invalid token')):
                # Call the decorated view
                response = decorated_view(mock_request)
                
                # Assert the view function was NOT called
                mock_view.assert_not_called()
                
                # Assert logger.warning was called with the error message
                mock_logger.warning.assert_called_once_with(
                    "API token validation failed: %s", 
                    "Invalid token"
                )
                
                # Assert response is an error
                assert response.status_code == 401
                assert b'Invalid token' in response.content

    def test_decorator_with_missing_token(self):
        """Test that the decorator blocks access when token is missing."""
        # Create a mock view function
        mock_view = Mock(return_value=JsonResponse({'status': 'success'}, status=200))
        
        # Apply the decorator
        decorated_view = api_token_required(mock_view)
        
        # Create a mock request
        mock_request = Mock()
        
        # Mock _validate_api_token to return failure for missing token
        with patch('api.gemilang.decorators.logger') as mock_logger:
            with patch('api.gemilang.views._validate_api_token', return_value=(False, 'API token is required')):
                # Call the decorated view
                response = decorated_view(mock_request)
                
                # Assert the view function was NOT called
                mock_view.assert_not_called()
                
                # Assert logger.warning was called
                mock_logger.warning.assert_called_once()
                
                # Assert response is an error
                assert response.status_code == 401

    def test_decorator_passes_args_and_kwargs(self):
        """Test that the decorator properly passes args and kwargs to the view."""
        # Create a mock view function
        mock_view = Mock(return_value=JsonResponse({'status': 'success'}, status=200))
        
        # Apply the decorator
        decorated_view = api_token_required(mock_view)
        
        # Create a mock request and additional arguments
        mock_request = Mock()
        extra_arg = 'test_arg'
        extra_kwarg = 'test_kwarg'
        
        # Mock _validate_api_token to return success
        with patch('api.gemilang.views._validate_api_token', return_value=(True, None)):
            # Call the decorated view with args and kwargs
            response = decorated_view(mock_request, extra_arg, keyword=extra_kwarg)
            
            # Assert the view function was called with all arguments
            mock_view.assert_called_once_with(mock_request, extra_arg, keyword=extra_kwarg)

    def test_decorator_preserves_function_metadata(self):
        """Test that the decorator preserves the original function's metadata."""
        # Create a view function with specific metadata
        def test_view(request):
            """Test view docstring."""
            return JsonResponse({'status': 'success'})
        
        test_view.__name__ = 'test_view'
        
        # Apply the decorator
        decorated_view = api_token_required(test_view)
        
        # Assert the function name is preserved
        assert decorated_view.__name__ == 'test_view'
        
        # Assert the docstring is preserved
        assert decorated_view.__doc__ == 'Test view docstring.'

    def test_decorator_with_multiple_error_messages(self):
        """Test decorator handles different error messages correctly."""
        error_messages = [
            'Token expired',
            'Token not found in database',
            'Insufficient permissions',
            'Token format invalid',
        ]
        
        for error_msg in error_messages:
            # Create a mock view function
            mock_view = Mock(return_value=JsonResponse({'status': 'success'}, status=200))
            
            # Apply the decorator
            decorated_view = api_token_required(mock_view)
            
            # Create a mock request
            mock_request = Mock()
            
            # Mock _validate_api_token to return failure with specific message
            with patch('api.gemilang.decorators.logger') as mock_logger:
                with patch('api.gemilang.views._validate_api_token', return_value=(False, error_msg)):
                    # Call the decorated view
                    response = decorated_view(mock_request)
                    
                    # Assert the error message is logged
                    mock_logger.warning.assert_called_once_with(
                        "API token validation failed: %s", 
                        error_msg
                    )
                    
                    # Assert response contains the error message
                    assert response.status_code == 401
                    assert error_msg.encode() in response.content

    def test_decorator_with_view_that_raises_exception(self):
        """Test that exceptions from the view are propagated correctly."""
        # Create a view function that raises an exception
        def failing_view(request):
            raise ValueError("Test exception")
        
        # Apply the decorator
        decorated_view = api_token_required(failing_view)
        
        # Create a mock request
        mock_request = Mock()
        
        # Mock _validate_api_token to return success
        with patch('api.gemilang.views._validate_api_token', return_value=(True, None)):
            # Call the decorated view and expect the exception
            with pytest.raises(ValueError, match="Test exception"):
                decorated_view(mock_request)

    def test_decorator_json_response_structure(self):
        """Test that the error JSON response has the correct structure."""
        # Create a mock view function
        mock_view = Mock()
        
        # Apply the decorator
        decorated_view = api_token_required(mock_view)
        
        # Create a mock request
        mock_request = Mock()
        
        # Mock _validate_api_token to return failure
        with patch('api.gemilang.views._validate_api_token', return_value=(False, 'Token validation failed')):
            # Call the decorated view
            response = decorated_view(mock_request)
            
            # Assert response is JsonResponse
            assert isinstance(response, JsonResponse)
            
            # Assert response structure
            import json
            response_data = json.loads(response.content)
            assert 'error' in response_data
            assert response_data['error'] == 'Token validation failed'

    def test_decorator_with_valid_token_returns_view_response_directly(self):
        """Test that decorator returns the view's response without modification."""
        # Create a custom response
        expected_response = JsonResponse({'custom': 'data', 'value': 42}, status=201)
        
        # Create a view that returns this response
        mock_view = Mock(return_value=expected_response)
        
        # Apply the decorator
        decorated_view = api_token_required(mock_view)
        
        # Create a mock request
        mock_request = Mock()
        
        # Mock _validate_api_token to return success
        with patch('api.gemilang.views._validate_api_token', return_value=(True, None)):
            # Call the decorated view
            response = decorated_view(mock_request)
            
            # Assert the response is exactly what the view returned
            assert response is expected_response
            assert response.status_code == 201

    def test_decorator_import_validation_function_inside_wrapper(self):
        """Test that _validate_api_token is imported inside the wrapper to avoid circular dependency."""
        # This test verifies the import happens inside the wrapper function
        # by checking that the import doesn't fail when the decorator is defined
        
        # Create a mock view
        mock_view = Mock(return_value=JsonResponse({'status': 'success'}))
        
        # Apply the decorator - this should not raise ImportError
        decorated_view = api_token_required(mock_view)
        
        # Verify the decorated view is callable
        assert callable(decorated_view)
        
        # Now call it with a mocked import
        mock_request = Mock()
        with patch('api.gemilang.views._validate_api_token', return_value=(True, None)):
            response = decorated_view(mock_request)
            assert response.status_code == 200

    def test_decorator_logger_receives_correct_context(self):
        """Test that the logger is instantiated with correct module name."""
        # This verifies that the logger at module level is created with 'decorators'
        from api.gemilang.decorators import logger
        
        # The logger should have been created with 'decorators' as the module name
        # We can verify it exists and is a logger instance
        assert logger is not None
        
        # Test that logging actually works when token validation fails
        mock_view = Mock()
        decorated_view = api_token_required(mock_view)
        mock_request = Mock()
        
        with patch('api.gemilang.decorators.logger') as mock_logger:
            with patch('api.gemilang.views._validate_api_token', return_value=(False, 'Test error')):
                decorated_view(mock_request)
                # Verify the logger.warning was called with the exact format string
                assert mock_logger.warning.called
                call_args = mock_logger.warning.call_args
                assert call_args[0][0] == "API token validation failed: %s"
                assert call_args[0][1] == "Test error"

    def test_decorator_with_empty_error_message(self):
        """Test decorator handles empty error message correctly."""
        mock_view = Mock(return_value=JsonResponse({'status': 'success'}))
        decorated_view = api_token_required(mock_view)
        mock_request = Mock()
        
        # Test with empty string error message
        with patch('api.gemilang.decorators.logger') as mock_logger:
            with patch('api.gemilang.views._validate_api_token', return_value=(False, '')):
                response = decorated_view(mock_request)
                
                # Should still return 401
                assert response.status_code == 401
                
                # Logger should be called with empty string
                mock_logger.warning.assert_called_once_with(
                    "API token validation failed: %s", 
                    ""
                )

    def test_decorator_with_none_error_message(self):
        """Test decorator handles None error message correctly."""
        mock_view = Mock(return_value=JsonResponse({'status': 'success'}))
        decorated_view = api_token_required(mock_view)
        mock_request = Mock()
        
        # Test with None error message
        with patch('api.gemilang.decorators.logger') as mock_logger:
            with patch('api.gemilang.views._validate_api_token', return_value=(False, None)):
                response = decorated_view(mock_request)
                
                # Should still return 401
                assert response.status_code == 401
                
                # Logger should be called with None
                mock_logger.warning.assert_called_once_with(
                    "API token validation failed: %s", 
                    None
                )
