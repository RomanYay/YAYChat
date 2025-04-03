import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import pyaudio
import socket
import threading
import wave
import struct
import pickle
import os
import json
from datetime import datetime

class VoiceChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Голосовой чат")
        self.root.geometry("800x600")  # Увеличиваем размер окна
        
        # Настройки аудио
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 44100
        
        # Сетевые настройки
        self.socket = None
        self.is_server = False
        self.is_connected = False
        self.clients = []  # Список подключенных клиентов
        self.client_sockets = []  # Сокеты подключенных клиентов
        
        # Никнейм
        self.nickname = "Пользователь"
        
        # Инициализация PyAudio
        self.p = pyaudio.PyAudio()
        
        # Получение списка аудио устройств
        self.input_devices = self.get_input_devices()
        
        # Создание элементов интерфейса
        self.create_widgets()
        
        # Флаги для управления потоком
        self.is_recording = False
        self.is_playing = False
        
    def get_input_devices(self):
        devices = []
        for i in range(self.p.get_device_count()):
            device_info = self.p.get_device_info_by_index(i)
            if device_info.get('maxInputChannels') > 0:  # Только устройства ввода
                devices.append((i, device_info.get('name')))
        return devices
        
    def create_widgets(self):
        # Создание вкладок
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both', padx=5, pady=5)
        
        # Вкладка голосового чата
        self.voice_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.voice_frame, text='Голосовой чат')
        
        # Вкладка текстового чата
        self.text_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.text_frame, text='Текстовый чат')
        
        # Создание виджетов для голосового чата
        self.create_voice_widgets()
        
        # Создание виджетов для текстового чата
        self.create_text_widgets()
        
    def create_voice_widgets(self):
        # Фрейм для никнейма
        self.nickname_frame = ttk.Frame(self.voice_frame)
        self.nickname_frame.pack(pady=5)
        ttk.Label(self.nickname_frame, text="Ваш никнейм:").pack(side=tk.LEFT)
        self.nickname_entry = ttk.Entry(self.nickname_frame)
        self.nickname_entry.pack(side=tk.LEFT, padx=5)
        self.nickname_entry.insert(0, self.nickname)
        ttk.Button(self.nickname_frame, text="Изменить", command=self.change_nickname).pack(side=tk.LEFT)
        
        # Фрейм для выбора режима
        self.mode_frame = ttk.Frame(self.voice_frame)
        self.mode_frame.pack(pady=5)
        
        self.mode_var = tk.StringVar(value="client")
        ttk.Radiobutton(self.mode_frame, text="Клиент", variable=self.mode_var, 
                       value="client", command=self.toggle_mode).pack(side=tk.LEFT)
        ttk.Radiobutton(self.mode_frame, text="Сервер", variable=self.mode_var, 
                       value="server", command=self.toggle_mode).pack(side=tk.LEFT)
        
        # Поле для ввода IP-адреса
        self.ip_frame = ttk.Frame(self.voice_frame)
        self.ip_frame.pack(pady=5)
        ttk.Label(self.ip_frame, text="IP:").pack(side=tk.LEFT)
        self.ip_entry = ttk.Entry(self.ip_frame)
        self.ip_entry.pack(side=tk.LEFT)
        self.ip_entry.insert(0, "localhost")
        
        # Поле для ввода порта
        self.port_frame = ttk.Frame(self.voice_frame)
        self.port_frame.pack(pady=5)
        ttk.Label(self.port_frame, text="Порт:").pack(side=tk.LEFT)
        self.port_entry = ttk.Entry(self.port_frame)
        self.port_entry.pack(side=tk.LEFT)
        self.port_entry.insert(0, "5000")
        
        # Выбор микрофона
        self.mic_frame = ttk.Frame(self.voice_frame)
        self.mic_frame.pack(pady=5)
        ttk.Label(self.mic_frame, text="Микрофон:").pack(side=tk.LEFT)
        self.mic_var = tk.StringVar()
        self.mic_combo = ttk.Combobox(self.mic_frame, textvariable=self.mic_var, state="readonly")
        self.mic_combo['values'] = [device[1] for device in self.input_devices]
        if self.input_devices:
            self.mic_combo.set(self.input_devices[0][1])
        self.mic_combo.pack(side=tk.LEFT)
        
        # Кнопка подключения
        self.connect_button = ttk.Button(self.voice_frame, text="Подключиться", command=self.connect)
        self.connect_button.pack(pady=10)
        
        # Кнопка начала/остановки записи
        self.record_button = ttk.Button(self.voice_frame, text="Начать запись", command=self.toggle_recording)
        self.record_button.pack(pady=10)
        self.record_button.config(state=tk.DISABLED)
        
        # Статус подключения
        self.status_label = ttk.Label(self.voice_frame, text="Статус: Отключено")
        self.status_label.pack(pady=10)
        
        # Список подключенных пользователей
        self.users_frame = ttk.LabelFrame(self.voice_frame, text="Подключенные пользователи")
        self.users_frame.pack(pady=5, padx=5, fill=tk.BOTH, expand=True)
        
        self.users_list = tk.Listbox(self.users_frame, height=5)
        self.users_list.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)
        
    def create_text_widgets(self):
        # Область чата
        self.chat_area = scrolledtext.ScrolledText(self.text_frame, wrap=tk.WORD, height=15, state=tk.DISABLED)
        self.chat_area.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)
        
        # Фрейм для ввода сообщения
        self.message_frame = ttk.Frame(self.text_frame)
        self.message_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Поле ввода сообщения
        self.message_entry = ttk.Entry(self.message_frame)
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Кнопка отправки
        self.send_button = ttk.Button(self.message_frame, text="Отправить", command=self.send_message)
        self.send_button.pack(side=tk.RIGHT, padx=5)
        
        # Привязка Enter к отправке сообщения
        self.message_entry.bind('<Return>', lambda e: self.send_message())
        
    def toggle_mode(self):
        if self.mode_var.get() == "server":
            self.ip_entry.config(state=tk.DISABLED)
            self.ip_entry.delete(0, tk.END)
            self.ip_entry.insert(0, "localhost")
        else:
            self.ip_entry.config(state=tk.NORMAL)
            
    def connect(self):
        if self.is_connected:
            self.disconnect()
        else:
            try:
                port = int(self.port_entry.get())
                if self.mode_var.get() == "server":
                    self.start_server(port)
                else:
                    self.start_client(port)
            except ValueError:
                messagebox.showerror("Ошибка", "Порт должен быть числом")
                
    def start_server(self, port):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(('', port))
        self.socket.listen(5)  # Разрешаем до 5 подключений
        self.is_server = True
        self.is_connected = True
        self.status_label.config(text="Статус: Ожидание подключения...")
        self.connect_button.config(text="Отключиться")
        self.record_button.config(state=tk.NORMAL)
        
        # Запуск потока для принятия подключений
        threading.Thread(target=self.accept_connections).start()
        
    def accept_connections(self):
        while self.is_connected:
            try:
                client, addr = self.socket.accept()
                # Запускаем поток для получения никнейма клиента
                threading.Thread(target=self.handle_new_client, args=(client, addr)).start()
            except:
                break
                
    def handle_new_client(self, client, addr):
        try:
            # Получаем никнейм клиента
            nickname_data = json.loads(client.recv(1024).decode())
            client_nickname = nickname_data['nickname']
            
            # Добавляем клиента в список
            self.clients.append(client_nickname)
            self.client_sockets.append(client)
            
            # Обновляем список пользователей
            self.update_users_list()
            
            # Отправляем всем клиентам обновленный список
            users_data = {
                'type': 'users_list',
                'users': self.clients
            }
            self.broadcast_data(json.dumps(users_data).encode())
            
            # Отправляем сообщение о подключении
            system_data = {
                'type': 'system',
                'message': f"{client_nickname} присоединился к чату",
                'time': datetime.now().strftime('%H:%M:%S')
            }
            self.broadcast_data(json.dumps(system_data).encode())
            
            # Запускаем поток для приема данных от клиента
            threading.Thread(target=self.receive_audio, args=(client, client_nickname)).start()
            
        except:
            self.remove_client(client)
            
    def update_users_list(self):
        self.users_list.delete(0, tk.END)
        for client in self.clients:
            self.users_list.insert(tk.END, client)
            
    def broadcast_data(self, data):
        disconnected_clients = []
        for client_socket in self.client_sockets:
            try:
                client_socket.send(data)
            except:
                disconnected_clients.append(client_socket)
                
        # Удаляем отключенных клиентов
        for client_socket in disconnected_clients:
            self.remove_client(client_socket)
            
    def remove_client(self, client_socket):
        if client_socket in self.client_sockets:
            index = self.client_sockets.index(client_socket)
            nickname = self.clients[index]
            self.clients.pop(index)
            self.client_sockets.pop(index)
            self.update_users_list()
            
            # Отправляем всем клиентам обновленный список
            users_data = {
                'type': 'users_list',
                'users': self.clients
            }
            self.broadcast_data(json.dumps(users_data).encode())
            
            # Отправляем сообщение о выходе
            system_data = {
                'type': 'system',
                'message': f"{nickname} покинул чат",
                'time': datetime.now().strftime('%H:%M:%S')
            }
            self.broadcast_data(json.dumps(system_data).encode())
            
            client_socket.close()
            
    def disconnect(self):
        if self.is_server:
            # Отправляем сообщение о отключении
            system_data = {
                'type': 'system',
                'message': f"{self.nickname} покинул чат",
                'time': datetime.now().strftime('%H:%M:%S')
            }
            self.broadcast_data(json.dumps(system_data).encode())
            # Закрываем все клиентские сокеты
            for client_socket in self.client_sockets:
                client_socket.close()
            self.client_sockets.clear()
            self.clients.clear()
            self.update_users_list()
        else:
            if self.socket:
                self.socket.close()
                
        self.is_connected = False
        self.is_recording = False
        self.status_label.config(text="Статус: Отключено")
        self.connect_button.config(text="Подключиться")
        self.record_button.config(state=tk.DISABLED)
        self.record_button.config(text="Начать запись")
        
    def toggle_recording(self):
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()
            
    def start_recording(self):
        self.is_recording = True
        self.record_button.config(text="Остановить запись")
        threading.Thread(target=self.record_audio).start()
        
    def stop_recording(self):
        self.is_recording = False
        self.record_button.config(text="Начать запись")
        
    def get_selected_device_index(self):
        selected_name = self.mic_var.get()
        for device in self.input_devices:
            if device[1] == selected_name:
                return device[0]
        return None
        
    def record_audio(self):
        device_index = self.get_selected_device_index()
        if device_index is None:
            messagebox.showerror("Ошибка", "Не выбран микрофон")
            return
            
        stream = self.p.open(format=self.FORMAT,
                           channels=self.CHANNELS,
                           rate=self.RATE,
                           input=True,
                           input_device_index=device_index,
                           frames_per_buffer=self.CHUNK)
        
        while self.is_recording and self.is_connected:
            try:
                data = stream.read(self.CHUNK)
                if self.is_server:
                    # Отправляем всем клиентам
                    self.broadcast_data(data)
                else:
                    # Отправляем только серверу
                    self.socket.send(data)
            except:
                self.disconnect()
                break
            
        stream.stop_stream()
        stream.close()
        
    def change_nickname(self):
        new_nickname = self.nickname_entry.get().strip()
        if new_nickname:
            self.nickname = new_nickname
            messagebox.showinfo("Успех", f"Ваш никнейм изменен на: {self.nickname}")
        else:
            messagebox.showerror("Ошибка", "Никнейм не может быть пустым")
            
    def send_message(self):
        if not self.is_connected:
            messagebox.showerror("Ошибка", "Не подключено к собеседнику")
            return
            
        message = self.message_entry.get().strip()
        if message:
            try:
                # Отправляем сообщение
                message_data = {
                    'type': 'text',
                    'message': message,
                    'time': datetime.now().strftime('%H:%M:%S'),
                    'nickname': self.nickname
                }
                
                # Отправляем сообщение в отдельном потоке
                threading.Thread(target=self.send_data, 
                               args=(json.dumps(message_data).encode(),)).start()
                
                # Добавляем сообщение в чат
                self.add_message_to_chat(self.nickname, message, message_data['time'])
                
                # Очищаем поле ввода
                self.message_entry.delete(0, tk.END)
            except:
                self.disconnect()
                
    def add_message_to_chat(self, sender, message, time):
        self.chat_area.insert(tk.END, f"[{time}] {sender}: {message}\n")
        self.chat_area.see(tk.END)
        
    def receive_audio(self, client_socket, client_nickname):
        stream = self.p.open(format=self.FORMAT,
                           channels=self.CHANNELS,
                           rate=self.RATE,
                           output=True)
        
        while self.is_connected:
            try:
                data = client_socket.recv(self.CHUNK)
                if data:
                    try:
                        # Пробуем декодировать как JSON
                        message_data = json.loads(data.decode())
                        if message_data['type'] == 'text':
                            self.add_message_to_chat(message_data['nickname'], message_data['message'], message_data['time'])
                        elif message_data['type'] == 'system':
                            self.add_message_to_chat("Система", message_data['message'], message_data['time'])
                        elif message_data['type'] == 'users_list':
                            self.update_users_list_from_server(message_data['users'])
                        elif message_data['type'] == 'request_users_list' and self.is_server:
                            # Отправляем текущий список пользователей
                            users_data = {
                                'type': 'users_list',
                                'users': self.clients
                            }
                            client_socket.send(json.dumps(users_data).encode())
                    except:
                        # Если не JSON, значит это аудио данные
                        stream.write(data)
                else:
                    break
            except:
                break
                
        stream.stop_stream()
        stream.close()
        if self.is_server:
            self.remove_client(client_socket)
        else:
            self.disconnect()
            
    def update_users_list_from_server(self, users):
        self.users_list.delete(0, tk.END)
        for user in users:
            self.users_list.insert(tk.END, user)
            
    def start_client(self, port):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.ip_entry.get(), port))
            self.is_connected = True
            self.status_label.config(text="Статус: Подключено")
            self.connect_button.config(text="Отключиться")
            self.record_button.config(state=tk.NORMAL)
            
            # Отправляем свой никнейм
            nickname_data = {
                'type': 'nickname',
                'nickname': self.nickname
            }
            self.socket.send(json.dumps(nickname_data).encode())
            
            # Запуск потока для приема данных
            threading.Thread(target=self.receive_audio, args=(self.socket, None)).start()
            
            # Запрашиваем текущий список пользователей
            request_data = {
                'type': 'request_users_list'
            }
            self.socket.send(json.dumps(request_data).encode())
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось подключиться: {str(e)}")
            
    def send_data(self, data):
        try:
            if self.is_server:
                self.broadcast_data(data)
            else:
                self.socket.send(data)
        except:
            self.disconnect()

if __name__ == "__main__":
    root = tk.Tk()
    app = VoiceChatApp(root)
    root.mainloop()
