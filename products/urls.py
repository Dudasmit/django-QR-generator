from django.urls import path
from .views import product_list, generate_qr,download_qr,download_all_qr, update_products_from_inriver, download_qr_zip, delete_all_qr

urlpatterns = [
    path('', product_list, name='product_list'),
    path('generate_qr/', generate_qr, name='generate_qr'),
    #path('download_qr/<str:filename>/', download_qr, name='download_qr'),
    path('download_qr/<int:product_id>/', download_qr_zip, name='download_qr'),
    path('download_all/', download_all_qr, name='download_all_qr'),
    path('update-from-inriver/', update_products_from_inriver, name='update_from_inriver'),
    path('delete_all_qr/', delete_all_qr, name='delete_all_qr'),
]
