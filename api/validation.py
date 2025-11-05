import re
import urllib.parse
from typing import Dict, List, Optional, Any, Type
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

class FieldValidator:
    def validate(self, value: Any) -> ValidationResult:
        raise NotImplementedError()

class KeywordValidator(FieldValidator):
    MAX_KEYWORD_LENGTH = 100
    MIN_KEYWORD_LENGTH = 2
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
    def _sanitize_keyword(keyword: str) -> str:
        keyword = re.sub(r'<[^>]+>', '', keyword)
        keyword = re.sub(r"[<>'\"\\\\\x00-\x1f\x7f-\x9f]", '', keyword)
        keyword = ' '.join(keyword.split())
        return keyword.strip()

    def validate(self, keyword: str) -> ValidationResult:
        errors = []
        if not keyword or not str(keyword).strip():
            errors.append(ValidationError(field='keyword', message='Search keyword is required', code='KEYWORD_REQUIRED'))
            return ValidationResult(is_valid=False, errors=errors)
        keyword = str(keyword).strip()
        if len(keyword) < self.MIN_KEYWORD_LENGTH:
            errors.append(ValidationError(field='keyword', message=f'Keyword must be at least {self.MIN_KEYWORD_LENGTH} characters long', code='KEYWORD_TOO_SHORT'))
        if len(keyword) > self.MAX_KEYWORD_LENGTH:
            errors.append(ValidationError(field='keyword', message=f'Keyword must not exceed {self.MAX_KEYWORD_LENGTH} characters', code='KEYWORD_TOO_LONG'))
        for pattern in self.MALICIOUS_PATTERNS:
            if re.search(pattern, keyword, re.IGNORECASE):
                errors.append(ValidationError(field='keyword', message='Contains invalid characters or malicious content', code='KEYWORD_MALICIOUS_CONTENT'))
                break
        if errors:
            return ValidationResult(is_valid=False, errors=errors)
        return ValidationResult(is_valid=True, errors=[], cleaned_data={'keyword': self._sanitize_keyword(keyword)})

class VendorValidator(FieldValidator):
    ALLOWED_VENDORS = ['depobangunan', 'gemilang', 'juragan_material', 'mitra10', 'government_wage']
    def validate(self, vendor: str) -> ValidationResult:
        errors = []
        if not vendor:
            errors.append(ValidationError(field='vendor', message='Vendor is required', code='VENDOR_REQUIRED'))
            return ValidationResult(is_valid=False, errors=errors)
        if vendor not in self.ALLOWED_VENDORS:
            errors.append(ValidationError(field='vendor', message=f'Invalid vendor. Allowed vendors: {", ".join(self.ALLOWED_VENDORS)}', code='VENDOR_INVALID'))
        if errors:
            return ValidationResult(is_valid=False, errors=errors)
        return ValidationResult(is_valid=True, errors=[], cleaned_data={'vendor': vendor.lower()})

class PaginationValidator(FieldValidator):
    MAX_PAGE_NUMBER = 50
    MIN_PAGE_NUMBER = 0
    def validate(self, page: Any) -> ValidationResult:
        errors = []
        try:
            page_int = int(page) if page is not None else 0
        except (ValueError, TypeError):
            errors.append(ValidationError(field='page', message='Page must be a valid integer', code='PAGE_INVALID_TYPE'))
            return ValidationResult(is_valid=False, errors=errors)
        if page_int < self.MIN_PAGE_NUMBER:
            errors.append(ValidationError(field='page', message=f'Page number must be at least {self.MIN_PAGE_NUMBER}', code='PAGE_TOO_LOW'))
        if page_int > self.MAX_PAGE_NUMBER:
            errors.append(ValidationError(field='page', message=f'Page number must not exceed {self.MAX_PAGE_NUMBER}', code='PAGE_TOO_HIGH'))
        if errors:
            return ValidationResult(is_valid=False, errors=errors)
        return ValidationResult(is_valid=True, errors=[], cleaned_data={'page': page_int})

class SortOptionValidator(FieldValidator):
    def validate(self, sort_by_price: Any) -> ValidationResult:
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
                errors.append(ValidationError(field='sort_by_price', message='Sort option must be a boolean value', code='SORT_INVALID_TYPE'))
                return ValidationResult(is_valid=False, errors=errors)
        if errors:
            return ValidationResult(is_valid=False, errors=errors)
        return ValidationResult(is_valid=True, errors=[], cleaned_data={'sort_by_price': cleaned_sort})

class URLValidator(FieldValidator):
    MALICIOUS_PATTERNS = KeywordValidator.MALICIOUS_PATTERNS
    def validate(self, url: str) -> ValidationResult:
        errors = []
        if not url:
            errors.append(ValidationError(field='url', message='URL is required', code='URL_REQUIRED'))
            return ValidationResult(is_valid=False, errors=errors)
        try:
            parsed = urllib.parse.urlparse(url)
            if parsed.scheme not in ['http', 'https']:
                errors.append(ValidationError(field='url', message='URL must use HTTP or HTTPS protocol', code='URL_INVALID_SCHEME'))
            if not parsed.netloc:
                errors.append(ValidationError(field='url', message='URL must have a valid domain', code='URL_INVALID_DOMAIN'))
            for pattern in self.MALICIOUS_PATTERNS:
                if re.search(pattern, url, re.IGNORECASE):
                    errors.append(ValidationError(field='url', message='Contains invalid characters or malicious content', code='URL_MALICIOUS_CONTENT'))
                    break
        except Exception:
            errors.append(ValidationError(field='url', message='Invalid URL format', code='URL_MALFORMED'))
        if errors:
            return ValidationResult(is_valid=False, errors=errors)
        return ValidationResult(is_valid=True, errors=[], cleaned_data={'url': url})

class InputValidator:
    keyword_validator: FieldValidator = KeywordValidator()
    vendor_validator: FieldValidator = VendorValidator()
    pagination_validator: FieldValidator = PaginationValidator()
    sort_option_validator: FieldValidator = SortOptionValidator()
    url_validator: FieldValidator = URLValidator()

    MAX_KEYWORD_LENGTH = KeywordValidator.MAX_KEYWORD_LENGTH
    MIN_KEYWORD_LENGTH = KeywordValidator.MIN_KEYWORD_LENGTH
    MAX_PAGE_NUMBER = PaginationValidator.MAX_PAGE_NUMBER
    MIN_PAGE_NUMBER = PaginationValidator.MIN_PAGE_NUMBER
    ALLOWED_VENDORS = VendorValidator.ALLOWED_VENDORS

    @staticmethod
    def validate_keyword(keyword: str) -> ValidationResult:
        return InputValidator.keyword_validator.validate(keyword)

    @staticmethod
    def validate_vendor(vendor: str) -> ValidationResult:
        return InputValidator.vendor_validator.validate(vendor)

    @staticmethod
    def validate_pagination(page: Any) -> ValidationResult:
        return InputValidator.pagination_validator.validate(page)

    @staticmethod
    def validate_sort_option(sort_by_price: Any) -> ValidationResult:
        return InputValidator.sort_option_validator.validate(sort_by_price)

    @staticmethod
    def validate_url(url: str) -> ValidationResult:
        return InputValidator.url_validator.validate(url)

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
        return ValidationResult(is_valid=len(all_errors) == 0, errors=all_errors, cleaned_data=cleaned_data if len(all_errors) == 0 else None)

    @staticmethod
    def _sanitize_keyword(keyword: str) -> str:
        return KeywordValidator._sanitize_keyword(keyword)


class RateLimitValidator(FieldValidator):
    def validate(self, user_id: str, max_requests_per_minute: int = 30) -> ValidationResult:
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