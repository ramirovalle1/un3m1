import requests
import base64
import webbrowser

class OdiloAPI:
    def __init__(self, client_id='E1148', client_secret='zmYrvarQie5igOX', user_id='3', password='1'):
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
        search_url = f'{self.base_url}/records?limit=60&offset=0&availability=true&query=allfields_txt:{query}'
        search_url += f'&order=relevance:desc'
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
