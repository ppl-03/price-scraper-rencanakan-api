import re
import urllib.parse
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class ValidationError:
    field: str
    message: str
    code: str


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[ValidationError]
    cleaned_data: Optional[Dict[str, Any]] = None


class InputValidator:
    MAX_KEYWORD_LENGTH = 100
    MIN_KEYWORD_LENGTH = 2
    MAX_PAGE_NUMBER = 50
    MIN_PAGE_NUMBER = 0
    
    ALLOWED_VENDORS = ['depobangunan', 'gemilang', 'juragan_material', 'mitra10']
    
    MALICIOUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'data:',
        r'vbscript:',
        r'on\w+\s*=',
        r'[<>"\']',
        r'\bunion\b.*\bselect\b',
        r'\bselect\b.*\bfrom\b',
        r'\binsert\b.*\binto\b',
        r'\bupdate\b.*\bset\b',
        r'\bdelete\b.*\bfrom\b',
        r'\bdrop\b.*\btable\b',
        r'--',
        r'/\*.*\*/',
    ]
    
    @staticmethod
    def _create_result(errors: List[ValidationError], cleaned_data: Dict[str, Any] = None) -> ValidationResult:
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            cleaned_data=cleaned_data if len(errors) == 0 else None
        )
    
    @staticmethod
    def _add_error(errors: List[ValidationError], field: str, message: str, code: str):
        errors.append(ValidationError(field=field, message=message, code=code))
    
    @staticmethod
    def _check_malicious_content(text: str, field: str) -> List[ValidationError]:
        errors = []
        for pattern in InputValidator.MALICIOUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                InputValidator._add_error(errors, field, 
                    'Contains invalid characters or malicious content', 
                    f'{field.upper()}_MALICIOUS_CONTENT')
                break
        return errors

    @staticmethod
    def validate_keyword(keyword: str) -> ValidationResult:
        errors = []
        
        if not keyword or not keyword.strip():
            InputValidator._add_error(errors, 'keyword', 'Search keyword is required', 'KEYWORD_REQUIRED')
            return InputValidator._create_result(errors)
        
        keyword = keyword.strip()
        
        if len(keyword) < InputValidator.MIN_KEYWORD_LENGTH:
            InputValidator._add_error(errors, 'keyword', 
                f'Keyword must be at least {InputValidator.MIN_KEYWORD_LENGTH} characters long', 
                'KEYWORD_TOO_SHORT')
        
        if len(keyword) > InputValidator.MAX_KEYWORD_LENGTH:
            InputValidator._add_error(errors, 'keyword', 
                f'Keyword must not exceed {InputValidator.MAX_KEYWORD_LENGTH} characters', 
                'KEYWORD_TOO_LONG')
        
        errors.extend(InputValidator._check_malicious_content(keyword, 'keyword'))
        
        return InputValidator._create_result(errors, {'keyword': InputValidator._sanitize_keyword(keyword)})

    @staticmethod
    def validate_vendor(vendor: str) -> ValidationResult:
        errors = []
        
        if not vendor:
            InputValidator._add_error(errors, 'vendor', 'Vendor is required', 'VENDOR_REQUIRED')
            return InputValidator._create_result(errors)
        
        if vendor not in InputValidator.ALLOWED_VENDORS:
            InputValidator._add_error(errors, 'vendor', 
                f'Invalid vendor. Allowed vendors: {", ".join(InputValidator.ALLOWED_VENDORS)}', 
                'VENDOR_INVALID')
        
        return InputValidator._create_result(errors, {'vendor': vendor.lower()})

    @staticmethod
    def validate_pagination(page: Any) -> ValidationResult:
        errors = []
        
        try:
            page_int = int(page) if page is not None else 0
        except (ValueError, TypeError):
            InputValidator._add_error(errors, 'page', 'Page must be a valid integer', 'PAGE_INVALID_TYPE')
            return InputValidator._create_result(errors)
        
        if page_int < InputValidator.MIN_PAGE_NUMBER:
            InputValidator._add_error(errors, 'page', 
                f'Page number must be at least {InputValidator.MIN_PAGE_NUMBER}', 'PAGE_TOO_LOW')
        
        if page_int > InputValidator.MAX_PAGE_NUMBER:
            InputValidator._add_error(errors, 'page', 
                f'Page number must not exceed {InputValidator.MAX_PAGE_NUMBER}', 'PAGE_TOO_HIGH')
        
        return InputValidator._create_result(errors, {'page': page_int})

    @staticmethod
    def validate_sort_option(sort_by_price: Any) -> ValidationResult:
        errors = []
        
        if sort_by_price is None:
            cleaned_sort = True
        elif isinstance(sort_by_price, bool):
            cleaned_sort = sort_by_price
        elif isinstance(sort_by_price, str):
            cleaned_sort = sort_by_price.lower() in ['true', '1', 'yes', 'on']
        else:
            try:
                cleaned_sort = bool(int(sort_by_price))
            except (ValueError, TypeError):
                InputValidator._add_error(errors, 'sort_by_price', 
                    'Sort option must be a boolean value', 'SORT_INVALID_TYPE')
                return InputValidator._create_result(errors)
        
        return InputValidator._create_result(errors, {'sort_by_price': cleaned_sort})

    @staticmethod
    def validate_url(url: str) -> ValidationResult:
        errors = []
        
        if not url:
            InputValidator._add_error(errors, 'url', 'URL is required', 'URL_REQUIRED')
            return InputValidator._create_result(errors)
        
        try:
            parsed = urllib.parse.urlparse(url)
            
            if parsed.scheme not in ['http', 'https']:
                InputValidator._add_error(errors, 'url', 
                    'URL must use HTTP or HTTPS protocol', 'URL_INVALID_SCHEME')
            
            if not parsed.netloc:
                InputValidator._add_error(errors, 'url', 
                    'URL must have a valid domain', 'URL_INVALID_DOMAIN')
            
            errors.extend(InputValidator._check_malicious_content(url, 'url'))
                    
        except Exception:
            InputValidator._add_error(errors, 'url', 'Invalid URL format', 'URL_MALFORMED')
        
        return InputValidator._create_result(errors, {'url': url})

    @staticmethod
    def validate_scraping_request(data: Dict[str, Any]) -> ValidationResult:
        all_errors = []
        cleaned_data = {}
        
        validators = [
            (InputValidator.validate_keyword, data.get('keyword', '')),
            (InputValidator.validate_vendor, data.get('vendor', '')),
            (InputValidator.validate_pagination, data.get('page')),
            (InputValidator.validate_sort_option, data.get('sort_by_price'))
        ]
        
        for validator, value in validators:
            result = validator(value)
            if not result.is_valid:
                all_errors.extend(result.errors)
            else:
                cleaned_data.update(result.cleaned_data)
        
        return InputValidator._create_result(all_errors, cleaned_data)

    @staticmethod
    def _sanitize_keyword(keyword: str) -> str:
        keyword = re.sub(r'<[^>]+>', '', keyword)
        keyword = re.sub(r'[<>"\'\\\x00-\x1f\x7f-\x9f]', '', keyword)
        keyword = ' '.join(keyword.split())
        return keyword.strip()


class RateLimitValidator:
    @staticmethod
    def validate_request_frequency(user_id: str, max_requests_per_minute: int = 30) -> ValidationResult:
        return ValidationResult(
            is_valid=True,
            errors=[],
            cleaned_data={'user_id': user_id}
        )


def validate_scraping_params(keyword: str, vendor: str, page: int = 0, sort_by_price: bool = True) -> ValidationResult:
    data = {
        'keyword': keyword,
        'vendor': vendor,
        'page': page,
        'sort_by_price': sort_by_price
    }
    
    return InputValidator.validate_scraping_request(data)


def get_validation_errors_dict(validation_result: ValidationResult) -> Dict[str, List[str]]:
    errors_dict = {}
    for error in validation_result.errors:
        if error.field not in errors_dict:
            errors_dict[error.field] = []
        errors_dict[error.field].append(error.message)
    
    return errors_dict