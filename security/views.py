from django.shortcuts import render
from .utils import sanitize_text

def show_scraped_data(request):
    raw_data = "<script>alert('xss')</script>Harga: 10000"
    clean_data = sanitize_text(raw_data)
    return render(request, "data.html", {"data": clean_data})
