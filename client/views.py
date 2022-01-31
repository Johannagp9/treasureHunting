from django.shortcuts import render
from django.http import HttpResponseRedirect
from .forms import CreateGameForm, GameInformationForm
import folium
import cloudinary.uploader
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from client.services.service import authenticate_user
from client.services.user_service import get_user_by_token, create_user
from django.core.cache import cache
from unicodedata import normalize
import re
import json
import requests

# Create your views here.
##TEMPLATES
LOGIN_TEMPLATE = "login.html"
REGISTER_USER_TEMPLATE = "register.html"
MAP_TEMPLATE = "client/map.html"

json_data = {
    "treasure_information":[

    ]
}


# Create your views here.
def login(request):
    return render(request, LOGIN_TEMPLATE)

def store_image_treasure(file):
    if len(file) > 0:
        result = cloudinary.uploader.upload(file, transformation=[
            {'width': 500, 'crop': 'scale', }])
        image_url = result["url"]
        return image_url


def normalizar(valor):
    valor = re.sub(
        r"([^n\u0300-\u036f]|n(?!\u0303(?![\u0300-\u036f])))[\u0300-\u036f]+", r"\1", 
        normalize( "NFD", valor), 0, re.I
    )
    return normalize("NFC", valor)


def generate_request_init(url, params={}):

    response = requests.get(url, params=params)
    
    if response.status_code >= 200 and response.status_code < 300:
        return response.json()


def response_2_dict(response):
    json_response = json.dumps(response)
    result = json.loads(json_response)  
    return result


def _get_coordinates(location):
    # TODO Debugging
    print("\n\n_get_coordinates")
    print(location)
    coordinates = cache.get(location)
    if coordinates is None:
        url_location = "https://nominatim.openstreetmap.org/search?q=" + location + "&format=json&addressdetails=1"
        response = generate_request_init(url_location, {})
        if response:
            result = response_2_dict(response)
            if result:
                lat = float(result[0]["lat"])
                long = float(result[0]["lon"])
                coordinates= [lat, long]
                cache.set(normalizar(location), coordinates, 3600)
                return coordinates
        return None
    print("coordinates")
    print(coordinates)
    return [coordinates['lat'], coordinates['long']]




def edit_game(request):

    maps = get_map([54.372158,18.638306])
    if request.method == "POST":
        form = CreateGameForm(request.POST, request.FILES)
        if form.is_valid():
            data = form.cleaned_data
            data['user_image'] = store_image_treasure(request.FILES["user_image"])
            print(data)
            return HttpResponseRedirect("/create/information")
    else:
        form = CreateGameForm()

    return render(request, "client/edit_game.html",{
         "form": form,
         "test": range(5),  #number of created Treasures in game
         "title": "Some name",   #Name of the game that user typed
         "treasure_description": "This is example of treasure description to make area look like normal area and some more informations here nothjing important", #it would be good to use here list to refer in templates in each iteration to different text
         "treasure_image": "https://www.polska.travel/images/pl-PL/glowne-miasta/gdansk/gdansk_motlawa_1170.jpg",
         "clue_description": "This is example of treasure description to make area look like normal area and some more informations here nothjing important",
         "map": maps
        })




def create_game(request):
    if request.method == "POST":
        form = CreateGameForm(request.POST, request.FILES)
        if form.is_valid():
            data = form.cleaned_data
            data['user_image'] = store_image_treasure(request.FILES["user_image"])
            print(data)
            return HttpResponseRedirect("/create/information")
    else:
        form = CreateGameForm()

    return render(request, "client/create_game.html",{
         "form": form,
        })




def game_information(request):


    print('request')
    print(request.method)
    if request.method == "GET":
        print(request.GET)
        form_information = GameInformationForm()

    # print(response_2_dict(request))

    #if len(json_data["treasure_information"]) > 0:
    #    maps = get_map([json_data["treasure_information"][0]["lat"],json_data["treasure_information"][0]["long"]])
    #else:
    #    maps = get_map([36.72016, -4.42034])

    #for i in range (0,len(json_data["treasure_information"])):
    #  pass  
    #maps = get_map([36.72016, -4.42034])
    #print("PRZED form_information->>>>>",request.POST.get('input_localization'))
    elif request.method == "POST":
        #print("form_information->>>>>",request.POST.get('input_localization'))
        #coordinates = _get_coordinates(request.POST['input_localization'])
        #print("game_information",coordinates)
        print(type(request))
        print(request.POST)
        print(type(request.POST))
        form_information = GameInformationForm()

        form_information = GameInformationForm(request.POST, request.FILES)
        if form_information.is_valid():
            #print("VALIDform_information->>>>>",request.POST.get('input_localization'))
            # TODO change with actual_location
            coordinates = _get_coordinates(request.POST.get('actual_location'))
            #coordinates = _get_coordinates(request.POST['location'])
            link = store_image_treasure(request.FILES["user_image_2"])
            json_object = {
                "description_treasure": form_information.cleaned_data["description_information"], 
                "treasure_image": link,
                "description_clue": form_information.cleaned_data["description_information_clue"],
                "lat": coordinates[0],
                "long": coordinates[1],
            }
            json_data["treasure_information"].append(json_object)
            print(json_data)
            if 'another' in request.POST:
                return HttpResponseRedirect("/create/information")
            if 'create' in request.POST: 
                
                return HttpResponseRedirect("/create")

    else:
        form_information = GameInformationForm()

    return render(request, "client/game_information.html",{
        "form_information": form_information,
    })




def get_map(coordinates):
    maps = folium.Map(location=coordinates, zoom_start=10)
    print("jestem get_map ->",coordinates)
    folium.Marker(
            location=coordinates
        ).add_to(maps)
    for i in range (0,len(json_data["treasure_information"])):
        folium.Marker(
            location=[json_data["treasure_information"][i]["lat"], json_data["treasure_information"][i]["long"]]
        ).add_to(maps)
    maps = maps._repr_html_()
    return maps

@csrf_exempt
def auth_user(request):
    id_token = request.POST.get('token')
    idinfo = authenticate_user(id_token)
    if idinfo is not None:
        return render(request, REGISTER_USER_TEMPLATE)
    else:
        return render(request, LOGIN_TEMPLATE)

def check_response(request, response):
    if isinstance(response, HttpResponse):
        if response.status_code == 401:
            return render(request, LOGIN_TEMPLATE)


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
def guardar_usuario(request):

    idinfo = request.session.get("token")
    user = {"google_id": idinfo['sub'],
               "name": request.POST.get("name"),
               "email": idinfo['email'],
               "admin": False}
    response = create_user(user, idinfo['sub'])

    if response:
        messages.success(request, "You just signed up for the treasure hunt!")
        users = get_user_by_token(idinfo['sub'])
        request.session['user'] = users[0]
        return redirect("/home")
    else:
        messages.error(request, "An error has occurred.")
        return render(request, REGISTER_USER_TEMPLATE)


@csrf_exempt
def logout(request):
    request.session['user'] = None
    return render(request, LOGIN_TEMPLATE)



@csrf_exempt
def index(request):
    return render(request, "base.html")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_exempt
def maps(request):
    print("CO TO JEST ->",request)
    coordinates = _get_coordinates(request.POST.get('location'))
    if (len(coordinates) == 2):
        maps = get_map(coordinates)
        return  render(request, MAP_TEMPLATE, {"maps":maps})
