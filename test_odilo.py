import requests
import base64
import webbrowser

class OdiloAPI:
    def __init__(self, client_id, client_secret, user_id, password):
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_id = user_id
        self.password = password
        self.access_token = None
        self.session = None
        self.base_url = 'https://uteca.unemi.edu.ec/opac/api/v2'

    def get_access_token(self):
        token_url = f'{self.base_url}/token'
        auth_str = f'{self.client_id}:{self.client_secret}'
        auth_b64 = base64.b64encode(auth_str.encode()).decode()
        headers = {
            'Authorization': f'Basic {auth_b64}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {
            'grant_type': 'client_credentials'
        }
        response = requests.post(token_url, headers=headers, data=data)
        token_data = response.json()
        self.access_token = token_data.get('token')

    def login(self):
        login_url = f'{self.base_url}/login'
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {
            'userId': self.user_id,
            'password': self.password
        }
        response = requests.post(login_url, headers=headers, data=data)
        session_data = response.json()
        self.session = session_data.get('session')
        return session_data

    def search_catalog(self, query):
        search_url = f'{self.base_url}/records?limit=24&offset=0&query=allfields_txt:{query}&availability=true'
        headers = {
            'Authorization': f'Bearer {self.access_token}'
        }
        response = requests.get(search_url, headers=headers)
        search_results = response.json()
        return search_results

    def get_title_availability(self, title_id, patron_id):
        availability_url = f'{self.base_url}/records/{title_id}/availability?patronId={patron_id}'
        headers = {
            'Authorization': f'Bearer {self.access_token}'
        }
        response = requests.get(availability_url, headers=headers)
        title_availability = response.json()
        return title_availability

    def checkout_title(self, title_id, patron_id):
        checkout_url = f'{self.base_url}/records/{title_id}/checkout'
        data = {
            'patronId': patron_id,
            'from': 'RECORD_SCREEN'
        }
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        response = requests.post(checkout_url, headers=headers, data=data)
        checkout_data = response.json()
        return checkout_data

    def open_title(self, download_url):
        # Verifica que la URL de descarga no esté vacía
        if download_url:
            # Abre la URL en el navegador web predeterminado
            webbrowser.open(download_url)
        else:
            print("La URL de descarga está vacía o no válida.")

    def return_title(self, checkout_id, patron_id):
        return_url = f'{self.base_url}/checkouts/{checkout_id}/return'
        data = {
            'patronId': patron_id
        }
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        response = requests.post(return_url, headers=headers, data=data)
        returned_checkout_data = response.json()
        return returned_checkout_data

# Uso de la clase OdiloAPI
if __name__ == "__main__":
    try:
        # Paso 1: Autorizar
        odilo = OdiloAPI(
            client_id='E1148',
            client_secret='zmYrvarQie5igOX',
            user_id='3',
            password='1'
        )
        odilo.get_access_token()

        # # Paso 2: Logear
        # login = odilo.login()
        # if 'errorCode' in login:
        #     raise NameError(login['errorCode'])

        # Paso 3: Buscar en el catálogo
        search_results = odilo.search_catalog('FUNDAMENTOS DE PROGRAMACIÓN')
        print(search_results)

        # Paso 4: De la lista extraida traer el id del libro que quieres mandar a consultar, y el patron_id es el id del usuario que hizo login
        #  Obtener disponibilidad de un título
        # title_id = '00028645'
        # patron_id = '002000414'
        # title_availability = odilo.get_title_availability(title_id, patron_id)
        # print(title_availability)
        #
        # # Paso 5: Realizar el Checkout
        # checkout_data = odilo.checkout_title(title_id, patron_id)
        # print(checkout_data)
        #
        # # Paso 7: Abrir el título (debes implementar este método)
        # odilo.open_title(checkout_data.get('downloadUrl'))
        #
        # # Paso 8: Devolver el título después del Checkout
        # returned_checkout_data = odilo.return_title(checkout_data.get('id'), patron_id)
        # print(returned_checkout_data)
        #
        # # Paso 9: Descargar
        # odilo.open_title(checkout_data.get('downloadUrl'))
    except Exception as ex:
        print(ex)