from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.shortcuts import redirect
from .models import Product
from .filters import ProductFilter
from .forms import QRForm
import qrcode
import tempfile
import shutil
from reportlab.graphics.barcode import qr as qr_code
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPM
import os
from django.conf import settings
from django.http import HttpResponse, FileResponse, Http404, JsonResponse
import requests
from PIL import Image
from io import BytesIO
import json
import zipfile
from django.core.paginator import Paginator
from datetime import date
from zipfile import ZipFile

TEMP_QR_DIR = os.path.join(tempfile.gettempdir(), 'qr_codes')
os.makedirs(TEMP_QR_DIR, exist_ok=True)

def product_list_old(request):
    
    product_filter = ProductFilter(request.GET, queryset=Product.objects.all().order_by('-name'))
    

    # Пагинация
    paginator = Paginator(product_filter.qs, 20)  # 20 товаров на страницу
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    qr_dir = os.path.join(settings.MEDIA_ROOT, 'qrcodes')
    has_qr_codes = any(os.scandir(qr_dir)) if os.path.exists(qr_dir) else False
    

    return render(request, 'products/product_list.html', {
        'filter': product_filter,
        'page_obj': page_obj,
        'qr_files': {},  # заглушка
        'show_download_all': False,
        'has_qr_codes': has_qr_codes,
    })

from django.db.models import Q

def product_list(request):
    show_without_qr = request.GET.get("without_qr") == "1"
    base_qs = Product.objects.all().order_by('-name')

    if show_without_qr:
        # Получаем ID товаров без QR
        ids_without_qr = []
        for product in base_qs:
            qr_path = os.path.join(settings.MEDIA_ROOT, 'qrcodes',  f"{product.name}.png")
            if not os.path.exists(qr_path):
                ids_without_qr.append(product.id)

        base_qs = base_qs.filter(id__in=ids_without_qr)  # ✅ это снова QuerySet

    product_filter = ProductFilter(request.GET, queryset=base_qs)

    paginator = Paginator(product_filter.qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    qr_dir = os.path.join(settings.MEDIA_ROOT, 'qrcodes')
    has_qr_codes = any(os.scandir(qr_dir)) if os.path.exists(qr_dir) else False

    return render(request, 'products/product_list.html', {
        'filter': product_filter,
        'page_obj': page_obj,
        'qr_files': {},
        'show_download_all': False,
        'has_qr_codes': has_qr_codes,
        'show_without_qr': show_without_qr,
    })



def delete_all_qr(request):
    qr_dir = os.path.join(settings.MEDIA_ROOT, 'qrcodes')  # или 'qr_codes', если используется такая папка

    if os.path.exists(qr_dir):
        shutil.rmtree(qr_dir)
        os.makedirs(qr_dir)  # Создаём заново пустую папку, если нужно
        messages.success(request, "All QR codes have been successfully removed.")
    else:
        messages.info(request, "No files were found for deletion.")

    return redirect('product_list')  # Возврат на главную


def generate_qr_old(request):
    if request.method == "POST":
        ids = request.POST.getlist('products')
        include_barcode = 'include_barcode' in request.POST
        form = QRForm(request.POST)
        if form.is_valid() and ids:
            products = Product.objects.filter(id__in=ids)
            for product in products:
                safe_name = product.name.replace(" ", "_")
                create_and_save_qr_code_eps("https://www.esschertdesign.com/qr/", safe_name, product.barcode, "qrcodes")
                '''
                qr_text = f"(01){product.barcode}"
                img = qrcode.make(qr_text)

                path_png = os.path.join(settings.MEDIA_ROOT, "qrcodes", f"{safe_name}.png")
                path_eps = os.path.join(settings.MEDIA_ROOT, "qrcodes", f"{safe_name}.eps")

                img.save(path_png)

                code = qr_code.QrCodeWidget(qr_text)
                bounds = code.getBounds()
                d = Drawing(bounds[2], bounds[3])
                d.add(code)
                renderPM.drawToFile(d, path_eps, fmt='EPS')
                '''

            return HttpResponse("QR-коды созданы.")
    else:
        form = QRForm()
        products = Product.objects.all()
    return render(request, 'products/generate_qr.html', {'form': form, 'products': products})

def generate_qr(request):
    if request.method == 'POST':
        selected_ids = request.POST.getlist('products')
        
        select_all = request.POST.get("select_all") == "1"
        
        
        include_barcode = 'include_barcode' in request.POST
        print(select_all)

        if not selected_ids:
            return render(request, 'products/generate_qr.html', {'returntolist': True})
            
            #return HttpResponse("Не выбраны товары.", status=400)
        if select_all:
            # Выбрать ВСЕ товары с учётом фильтра (не только текущую страницу)
            product_filter = ProductFilter(request.session.get("last_filter", {}), queryset=Product.objects.all())
            products = product_filter.qs
        else:
            products = Product.objects.filter(id__in=selected_ids)
            
        file_paths = []
        qr_root = os.path.join(settings.MEDIA_ROOT, 'qrcodes')
        os.makedirs(qr_root, exist_ok=True)

        for product in products:
            qr_text = f"{product.name}"
            if include_barcode:
                qr_text += f"\n{product.barcode}"

            #img = qrcode.make(qr_text)

            filename = f"{product.name.replace(' ', '_')}.png"
            
            #file_path = os.path.join(TEMP_QR_DIR, filename)
            
            #img.save(file_path)
            
            if create_and_save_qr_code_eps("https://www.esschertdesign.com/qr/", product.name, product.barcode,include_barcode, "qrcodes"):
                file_paths.append((product.id, filename))
            #print(file_paths)

        # Возвращаем HTML с кнопками скачивания
        product_filter = ProductFilter(request.GET, queryset=Product.objects.all().order_by('-name'))
        
        paginator = Paginator(product_filter.qs, 20)  # 20 товаров на страницу
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        return redirect('product_list')

    return HttpResponse("Метод не поддерживается", status=405)


def download_qr(request, filename):
    file_path = os.path.join(TEMP_QR_DIR, filename)
    if not os.path.exists(file_path):
        raise Http404("QR код не найден")
    return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=filename)

def download_qr_zip(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    base_path = f'media/qrcodes/'
    png_path = os.path.join(base_path, f"{product.name}.png")
    eps_path = os.path.join(base_path, f"{product.name}.eps")

    if not os.path.exists(png_path) or not os.path.exists(eps_path):
        return HttpResponse("QR-коды не найдены для этого товара.", status=404)

    buffer = BytesIO()
    with ZipFile(buffer, 'w') as zip_file:
        zip_file.write(png_path, arcname=f"{product.name}.png")
        zip_file.write(eps_path, arcname=f"{product.name}.eps")

    buffer.seek(0)
    response = FileResponse(buffer, as_attachment=True, filename=f"{product.name}_qr.zip")
    return response

def download_all_qr(request):
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zipf:
        for fname in os.listdir(os.path.join(settings.MEDIA_ROOT, 'qrcodes')):
            fpath = os.path.join(settings.MEDIA_ROOT, 'qrcodes', fname)
            zipf.write(fpath, arcname=fname)
    zip_buffer.seek(0)
    
    return HttpResponse(zip_buffer, content_type='application/zip', headers={
        'Content-Disposition': 'attachment; filename="qr_codes.zip"',
    })

def check_url_exists(url):
    try:
        response = requests.head(url, allow_redirects=True, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False



def remove_transparency(im, bg_color=(255, 255, 255)):
    """
    """
    # Only process if image has transparency (http://stackoverflow.com/a/1963146)
    if im.mode in ('RGBA', 'LA') or (im.mode == 'P' and 'transparency' in im.info):

        # Need to convert to RGBA if LA format due to a bug in PIL (http://stackoverflow.com/a/1963146)
        alpha = im.convert('RGBA').split()[-1]

        # Create a new background image of our matt color.
        # Must be RGBA because paste requires both images have the same format
        # (http://stackoverflow.com/a/8720632  and  http://stackoverflow.com/a/9459208)
        bg = Image.new("RGBA", im.size, bg_color + (255,))
        bg.paste(im, mask=alpha)
        return bg
    else:
        return im


def create_and_save_qr_code_eps(url, item, GTIN,include_barcode, folder):
    data_url = url +  item

    if check_url_exists(data_url):
        print("Ссылка существует!")
    else:
        print("Ссылка не доступна или не существует. " + item)
        #return False
    if include_barcode:
        # Добавляем штрих-код в данные QR-кода
        data = "01" + str(GTIN) + "8200" + data_url
    else:
        data =  data_url

    # Создание QR-кода
    qr = qrcode.QRCode(
    version=1,  # Размер (1 - самый маленький)
    error_correction=qrcode.constants.ERROR_CORRECT_L,  # Уровень коррекции ошибок
    box_size=10,  # Размер каждой "коробки" (пиксели)
    border=4,  # Толщина рамки (в коробках)
    )
    qr.add_data(data)
    qr.make(fit=True)

    # Создание изображения
    img = qr.make_image(fill_color="black", back_color="white")

    png_path = os.path.join(settings.MEDIA_ROOT, folder, f"{item}.png")
    #png_path = os.path.join(folder, f"{item}.png")
    # Сохранение изображения
    try:
        img.save(png_path)

    except Exception as e:
        return False
    
    #img_bw = img.convert("1")

    fig = Image.open(png_path)
    if fig.mode in ('RGBA', 'LA'):
        # https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html?highlight=eps#eps
        print('Current figure mode "{}" cannot be directly saved to .eps and should be converted (e.g. to "RGB")'.format(fig.mode))
        fig = remove_transparency(fig)
        fig = fig.convert('RGB')

    fig = remove_transparency(fig)
    fig = fig.convert('RGB')
    eps_path = os.path.join(settings.MEDIA_ROOT, folder, f"{item}.eps")
    #eps_path = os.path.join(folder, f"{item}.eps")
    
    try:
        fig.save(eps_path)

    except Exception as e:
        return False

    fig.close()
    return True
def get_inriver_token():
        return '7a2cec7e5ea298bbc2751c4d18a6530a'
    
def get_inriver_header():
        headers_inRiver = dict(Accept='application/json')
        headers_inRiver['Content-type'] = 'application/json'
        headers_inRiver['X-inRiver-APIKey'] = get_inriver_token()
        return headers_inRiver
    
def get_inriver_url():
        return 'https://api-prod1a-euw.productmarketingcloud.com'


def update_products_from_inriver(request):
    created_count = 0
    updated_count = 0
    skipped_count = 0
    json_request =  {
            "systemCriteria": [ ],
            "dataCriteria": [ {
                "fieldTypeId": "ItemIndicationWebshop",
                "value": "1",
                "operator": "Equal"
                }
                             ]
            }
    # Эмуляция запроса к Inriver — замените на настоящий API
    try:
        
        response = requests.post('{}/api/v1.0.0/query'.format(get_inriver_url()),
                                 headers= get_inriver_header(), data= json.dumps(json_request))
        
        response.raise_for_status()

        inriver_data = response.json()  # Ожидается список словарей с полями
    except Exception as e:
        print("Begin_",e)
        messages.error(request, f"Ошибка при подключении к Inriver: {e}")
        return redirect('product_list')


    for item in inriver_data['entityIds']:
        ext_id = item
        if Product.objects.filter(external_id=ext_id).exists():
            skipped_count += 1
            continue
        if not ext_id:
            continue
        resp_get_linkEntityId = requests.get('{}/api/v1.0.0/entities/{}/fieldvalues'.format(get_inriver_url(),int(ext_id)),headers= get_inriver_header())
        if resp_get_linkEntityId.text != '[]' and resp_get_linkEntityId.status_code == 200:
            json_data = resp_get_linkEntityId.json()
            
            product, created = Product.objects.update_or_create(
                external_id=ext_id,
                defaults={
                    'name': next((item_["value"] for item_ in json_data if item_["fieldTypeId"] == "ItemCode"), None),
                    'barcode': next((item["value"] for item in json_data if item["fieldTypeId"] == "ItemGTIN"), None),
                    'created_at': date.today(),
                    'group': 'inriver',
                    'show_on_site': True,
                    }
                )
        if created:
            created_count += 1
        else:
            updated_count += 1

    messages.success(
        request,
        f"The update has been finalized: {created_count} added, {updated_count} updated, {skipped_count} missing (duplicates)."
    )
    return redirect('product_list')