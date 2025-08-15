# -*- coding: utf-8 -*-
# kivy_app_sok.py (UI - Hoàn chỉnh với Backup/Restore)

import os, threading, io, qrcode, json, random
from datetime import datetime
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition, NoTransition
from kivy.uix.modalview import ModalView
from kivy.clock import Clock
from kivy.utils import get_color_from_hex
from kivy.graphics import Color, Rectangle, RoundedRectangle, Ellipse, PushMatrix, PopMatrix, Scale
from kivy.core.clipboard import Clipboard
from kivy.uix.image import Image
from kivy.core.image import Image as CoreImage
from kivy.animation import Animation
from kivy.properties import NumericProperty
from kivy.core.window import Window

from backend import BackendLogic

# --- Cấu hình thiết kế & tài nguyên ---
PRIMARY_ACCENT = get_color_from_hex("#8A2BE2")
TEXT_COLOR_LIGHT = (1, 1, 1, 0.95)
TEXT_COLOR_DARK = (0.1, 0.1, 0.2, 1)
CARD_BACKGROUND_COLOR = (0.1, 0.05, 0.15, 0.65)

AURORA_COLORS = [
    get_color_from_hex("#8A2BE2"), get_color_from_hex("#4B0082"),
    get_color_from_hex("#00008B"), get_color_from_hex("#483D8B")
]

ASSETS_DIR = 'assets'
FONT_REGULAR = os.path.join(ASSETS_DIR, 'BeVietnamPro-Regular.ttf')
FONT_BOLD = os.path.join(ASSETS_DIR, 'BeVietnamPro-Bold.ttf')
FONT_ICON = os.path.join(ASSETS_DIR, 'DejaVuSans.ttf')
LOGO_FILE = os.path.join(ASSETS_DIR, 'logo.png')
ICON_FILE = os.path.join(ASSETS_DIR, 'icon.png')

# --- Các lớp Widget và AuroraBackground giữ nguyên ---
class AuroraBackground(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.blobs = []
        with self.canvas.before:
            Color(0.06, 0.02, 0.1, 1); self.bg_rect = Rectangle(size=self.size, pos=self.pos)
            for i in range(4):
                color = random.choice(AURORA_COLORS); color[3] = random.uniform(0.1, 0.35)
                self.blobs.append({'color': Color(rgba=color), 'shape': Ellipse(pos=(random.uniform(-0.5, 0.5) * self.width, random.uniform(-0.5, 0.5) * self.height),size=(random.uniform(0.8, 1.5) * self.width, random.uniform(0.8, 1.5) * self.height))})
        self.bind(size=self._update_rect, pos=self._update_rect)
        Clock.schedule_once(self.animate_blobs)
    def _update_rect(self, i, v): self.bg_rect.pos=i.pos; self.bg_rect.size=i.size
    def animate_blobs(self, *args):
        for blob in self.blobs:
            anim = (Animation(pos=(random.uniform(-0.5, 0.5) * self.width, random.uniform(-0.5, 0.5) * self.height), size=(random.uniform(0.8, 1.5) * self.width, random.uniform(0.8, 1.5) * self.height), duration=random.uniform(15, 25)) + Animation(pos=(random.uniform(-0.5, 0.5) * self.width, random.uniform(-0.5, 0.5) * self.height), size=(random.uniform(0.8, 1.5) * self.width, random.uniform(0.8, 1.5) * self.height), duration=random.uniform(15, 25)))
            anim.repeat = True; anim.start(blob['shape'])

class Card(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation='vertical'; self.size_hint=(1,None); self.padding=(25,25); self.spacing=15
        with self.canvas.before: Color(*CARD_BACKGROUND_COLOR); self.rect=RoundedRectangle(size=self.size,pos=self.pos,radius=[20])
        self.bind(pos=self.update_rect, size=self.update_rect)
    def update_rect(self, *args): self.rect.pos=self.pos; self.rect.size=self.size

class AppButton(Button):
    def __init__(self, **kwargs):
        kwargs.setdefault('background_color', PRIMARY_ACCENT); kwargs.setdefault('font_name', FONT_BOLD)
        kwargs.setdefault('color', TEXT_COLOR_LIGHT); kwargs.setdefault('background_normal', ''); kwargs.setdefault('size_hint_y', None); kwargs.setdefault('height', 50)
        super().__init__(**kwargs)
        
class ThemedLabel(Label):
    def __init__(self, **kwargs):
        kwargs.setdefault('font_name', FONT_REGULAR); kwargs.setdefault('color', TEXT_COLOR_LIGHT)
        super().__init__(**kwargs)
        
class ThemedTextInput(TextInput):
    def __init__(self, **kwargs):
        kwargs.setdefault('background_color', (0,0,0,0.2)); kwargs.setdefault('foreground_color', TEXT_COLOR_LIGHT)
        kwargs.setdefault('cursor_color', PRIMARY_ACCENT); kwargs.setdefault('font_name', FONT_REGULAR)
        super().__init__(**kwargs)

class BaseScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()
        self.backend = self.app.backend

# --- Màn hình Dashboard (Thêm nút "Sao lưu Private Key") ---
class DashboardScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Bố cục giao diện
        root_scroll=ScrollView(size_hint=(1,1),bar_width=0);layout=BoxLayout(orientation='vertical',padding=20,spacing=20,size_hint_y=None);layout.bind(minimum_height=layout.setter('height'))
        
        # Thẻ tài khoản
        acc_card=Card(size_hint_y=None); acc_card.bind(minimum_height=acc_card.setter('height'))
        acc_card.add_widget(ThemedLabel(text="Tài khoản",font_size='18sp',font_name=FONT_BOLD,color=PRIMARY_ACCENT, size_hint_y=None, height=40))
        self.balance_label=ThemedLabel(text="Số dư: Đang tải...",font_size='22sp',font_name=FONT_BOLD, size_hint_y=None, height=40)
        acc_card.add_widget(self.balance_label)
        addr_layout=BoxLayout(orientation='horizontal',size_hint_y=None,height=44,spacing=10)
        self.address_input=ThemedTextInput(text="Đang tải ví...",readonly=True,multiline=False)
        copy_btn=Button(text="Copy",size_hint_x=None,width=100,font_name=FONT_BOLD);copy_btn.bind(on_press=self.copy_address)
        addr_layout.add_widget(self.address_input);addr_layout.add_widget(copy_btn);acc_card.add_widget(addr_layout)
        act_btns_layout=BoxLayout(orientation='horizontal',size_hint_y=None,height=50,spacing=20)
        send_nav_btn=AppButton(text="Gửi SOK",background_color=get_color_from_hex("#3498db"));send_nav_btn.bind(on_press=lambda x:setattr(self.manager,'current','miner'))
        recv_btn=AppButton(text="Nhận (QR)",background_color=get_color_from_hex("#2ecc71"));recv_btn.bind(on_press=self.show_qr_popup)
        act_btns_layout.add_widget(send_nav_btn);act_btns_layout.add_widget(recv_btn);acc_card.add_widget(act_btns_layout)
        
        # [MỚI] Nút sao lưu key
        backup_btn = AppButton(text="Sao lưu Private Key", background_color=get_color_from_hex("#f39c12")); backup_btn.bind(on_press=self.show_password_prompt_for_backup)
        acc_card.add_widget(backup_btn)

        # Thẻ mạng
        net_card=Card(height=120,size_hint_y=None);net_card.add_widget(ThemedLabel(text="Trạng thái Mạng",font_size='18sp',font_name=FONT_BOLD,color=PRIMARY_ACCENT));self.height_label=ThemedLabel(text="Khối: ...",font_size='16sp');self.status_label=ThemedLabel(text="Mạng: ...",font_size='16sp');net_card.add_widget(self.height_label);net_card.add_widget(self.status_label)
        self.refresh_button=AppButton(text="Làm mới Bảng tin");self.refresh_button.bind(on_press=self.refresh_data);layout.add_widget(acc_card);layout.add_widget(net_card);layout.add_widget(self.refresh_button);root_scroll.add_widget(layout);self.add_widget(root_scroll)

    # [MỚI] Hàm hiển thị popup yêu cầu mật khẩu trước khi sao lưu
    def show_password_prompt_for_backup(self, instance):
        content=BoxLayout(orientation='vertical',padding=20,spacing=10);popup=ModalView(size_hint=(0.8,None),height=280,background_color=(1,1,1,0.95))
        content.add_widget(Label(text="Xác thực để Sao lưu",font_size='20sp',color=TEXT_COLOR_DARK,font_name=FONT_BOLD))
        content.add_widget(Label(text="Nhập mật khẩu ví của bạn để xem Private Key.",color=TEXT_COLOR_DARK,font_name=FONT_REGULAR))
        pass_input = TextInput(hint_text="Nhập mật khẩu", password=True, multiline=False, foreground_color=TEXT_COLOR_DARK, background_color=(.9,.9,.9,1))
        content.add_widget(pass_input)
        confirm_btn = Button(text="Xác nhận", size_hint_y=None, height=50, font_name=FONT_BOLD)
        content.add_widget(confirm_btn)
        
        def do_confirm(*args):
            password = pass_input.text
            # Thử load lại ví với mật khẩu đã nhập để xác thực
            success, msg = self.backend.load_wallet_from_file(password)
            popup.dismiss()
            if success:
                private_key = self.backend.get_private_key_for_backup()
                if private_key:
                    # Gọi lại popup hiển thị key an toàn
                    self.app.show_backup_popup(private_key, is_creation=False)
                else:
                    self.app.show_popup("Lỗi", "Không thể lấy được Private Key.")
            else:
                self.app.show_popup("Lỗi", "Mật khẩu không chính xác.")

        confirm_btn.bind(on_press=do_confirm)
        popup.add_widget(content)
        popup.open()

    # Các hàm khác của DashboardScreen giữ nguyên
    def on_enter(self,*args):
        if self.backend and self.backend.wallet:self.address_input.text=self.backend.wallet.get_address();self.refresh_data(self.refresh_button)
    def refresh_data(self,instance):instance.disabled=True;instance.text="Đang tải...";threading.Thread(target=self._update_ui_thread,args=(instance,),daemon=True).start()
    def _update_ui_thread(self,btn_instance):data=self.backend.refresh_dashboard();Clock.schedule_once(lambda dt:self._finalize_refresh(data,btn_instance))
    def _finalize_refresh(self,data,btn_instance):
        if data and data.get('profile') and data.get('stats'): self._update_labels(data)
        else: self.app.show_popup("Lỗi", "Không thể tải dữ liệu Bảng tin từ server.")
        btn_instance.disabled=False;btn_instance.text="Làm mới Bảng tin"
    def _update_labels(self,data):
        profile=data.get('profile',{});stats=data.get('stats',{})
        self.balance_label.text=f"Số dư: {float(profile.get('sok_balance',0)):.8f} SOK"
        self.status_label.text=f"Mạng: {stats.get('status','N/A')}"
        self.height_label.text=f"Khối: {stats.get('blockchain_height','N/A')}"
    def copy_address(self,instance):
        if self.address_input.text and self.address_input.text!="Đang tải ví...":Clipboard.copy(self.address_input.text);self.app.show_popup("Thành công","Địa chỉ ví đã được sao chép!")
    def show_qr_popup(self,instance):
        if not self.backend.wallet:return
        addr=self.backend.wallet.get_address();content=BoxLayout(orientation='vertical',padding=20,spacing=10);content.add_widget(Label(text="Quét mã này để nhận SOK",font_size='18sp',size_hint_y=None,height=40,color=TEXT_COLOR_DARK,font_name=FONT_BOLD));qr_img=qrcode.make(addr);buffer=io.BytesIO();qr_img.save(buffer,format='PNG');buffer.seek(0);core_img=CoreImage(buffer,ext='png');qr_widget=Image(texture=core_img.texture);content.add_widget(qr_widget);addr_label=TextInput(text=addr,readonly=True,size_hint_y=None,height=80,multiline=True,font_name=FONT_REGULAR,foreground_color=TEXT_COLOR_DARK,background_color=(.9,.9,.9,1));content.add_widget(addr_label);close_btn=Button(text='Đóng',size_hint_y=None,height=50,font_name=FONT_BOLD);content.add_widget(close_btn);popup=ModalView(size_hint=(0.9,0.8),background_color=(1,1,1,0.95));popup.add_widget(content);close_btn.bind(on_press=popup.dismiss);popup.open()

# --- Các màn hình History, Website, Miner, MainScreen giữ nguyên ---
class HistoryScreen(BaseScreen):
    #... (Mã giữ nguyên)
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout=BoxLayout(orientation='vertical',padding=10,spacing=10);header=BoxLayout(size_hint=(1,None),height=50,spacing=10);header.add_widget(ThemedLabel(text="Lịch sử Giao dịch",font_size='24sp',font_name=FONT_BOLD));self.refresh_button=AppButton(text="Làm mới",size_hint=(None,1),width=120);self.refresh_button.bind(on_press=self.refresh_history);header.add_widget(self.refresh_button);scroll=ScrollView(size_hint=(1,1),bar_width=0);self.history_grid=GridLayout(cols=1,spacing=10,size_hint_y=None);self.history_grid.bind(minimum_height=self.history_grid.setter('height'));scroll.add_widget(self.history_grid);layout.add_widget(header);layout.add_widget(scroll);self.add_widget(layout)
    def on_enter(self,*args):self.refresh_history(self.refresh_button)
    def refresh_history(self,instance):
        if instance:instance.disabled=True;instance.text="Tải..."
        threading.Thread(target=self._fetch_history_thread,args=(instance,),daemon=True).start()
    def _fetch_history_thread(self,btn_instance):history_data=self.backend.get_transaction_history();Clock.schedule_once(lambda dt:self.populate_history(history_data,btn_instance))
    def populate_history(self,history,btn_instance):
        self.history_grid.clear_widgets()
        if history is None or (isinstance(history, dict) and 'error' in history):
            error_msg = (history or {}).get('error', "Không thể tải lịch sử từ server.")
            card = Card(height=100, size_hint_y=None); card.add_widget(ThemedLabel(text=error_msg)); self.history_grid.add_widget(card)
        elif not history:
            card = Card(height=100, size_hint_y=None); card.add_widget(ThemedLabel(text="Chưa có giao dịch nào.")); self.history_grid.add_widget(card)
        else:
            sorted_history=sorted(history,key=lambda x:x.get('timestamp',0),reverse=True)
            for tx in sorted_history:
                tx_widget=self.create_transaction_card(tx)
                if tx_widget:self.history_grid.add_widget(tx_widget)
        if btn_instance:btn_instance.disabled=False;btn_instance.text="Làm mới"
    def create_transaction_card(self,tx_data):
        if not isinstance(tx_data,dict):return None
        card=Card(height=100,size_hint_y=None,padding=[15,10],spacing=10);main_layout=BoxLayout(orientation='horizontal',spacing=10);icon=ThemedLabel(font_size='28sp',size_hint_x=0.15,font_name=FONT_ICON);info_layout=BoxLayout(orientation='vertical',spacing=2);primary_info=ThemedLabel(markup=True,halign='left',valign='middle',font_size='16sp',font_name=FONT_BOLD);secondary_info=ThemedLabel(markup=True,halign='left',valign='top',font_size='12sp',color=(.8,.8,.8,1));action_btn=Button(text="...",size_hint_x=None,width=50,font_size='20sp',background_color=(0,0,0,0),font_name=FONT_ICON);action_btn.bind(on_press=lambda i,d=tx_data:self.show_copy_menu(i,d))
        try:amount_str=f"{float(tx_data.get('amount','0')):.8f}";ts=tx_data.get('timestamp');time_str=datetime.fromtimestamp(ts).strftime('%d/%m/%Y %H:%M')if ts else'N/A'
        except:amount_str,time_str="Lỗi","Lỗi"
        sender,rcpt,treasury=tx_data.get('from','N/A'),tx_data.get('to','N/A'),self.backend.treasury_address
        tx_type=tx_data.get('type','');my_addr=self.backend.wallet.get_address()
        if tx_type=='reward'or sender=="0":icon.text,icon.color="★",get_color_from_hex("#f1c40f");primary_info.text=f"[b]+ {amount_str} SOK[/b]";secondary_info.text=f"Phần thưởng mạng lưới - {time_str}"
        elif tx_type=='fee':icon.text,icon.color="F",get_color_from_hex("#95a5a6");primary_info.text=f"[b]- {amount_str} SOK[/b]";secondary_info.text=f"Phí giao dịch - {time_str}"
        elif rcpt==my_addr:icon.text,icon.color="↑",get_color_from_hex("#2ecc71");primary_info.text=f"[b]+ {amount_str} SOK[/b]";secondary_info.text=f"Nhận từ: {sender[:15]}... - {time_str}"
        elif sender==my_addr:
            if rcpt==treasury:icon.text,icon.color="$",get_color_from_hex("#3498db");primary_info.text=f"[b]- {amount_str} SOK[/b]";secondary_info.text=f"Nạp tiền cho Website - {time_str}"
            else:icon.text,icon.color="↓",get_color_from_hex("#e74c3c");primary_info.text=f"[b]- {amount_str} SOK[/b]";secondary_info.text=f"Gửi đến: {rcpt[:15]}... - {time_str}"
        else:primary_info.text="Giao dịch không xác định"
        primary_info.bind(size=primary_info.setter('text_size'));secondary_info.bind(size=secondary_info.setter('text_size'));info_layout.add_widget(primary_info);info_layout.add_widget(secondary_info);main_layout.add_widget(icon);main_layout.add_widget(info_layout);main_layout.add_widget(action_btn);card.add_widget(main_layout);return card
    def show_copy_menu(self,btn_instance,tx_data):
        popup=ModalView(size_hint=(None,None),size=(250,200),auto_dismiss=True,background_color=(1,1,1,0.95));btn_pos=btn_instance.to_window(*btn_instance.pos);popup.pos=(btn_pos[0]-popup.width+btn_instance.width,btn_pos[1]-popup.height/2);menu_layout=BoxLayout(orientation='vertical',padding=10,spacing=5)
        def copy_and_dismiss(txt,name):
            if txt and txt!='N/A':Clipboard.copy(txt);self.app.show_popup("Thành công",f"Đã sao chép {name}.")
            popup.dismiss()
        sender=tx_data.get('from','N/A')
        if sender not in["0",'N/A']:menu_layout.add_widget(Button(text="Copy ví gửi",on_press=lambda x:copy_and_dismiss(sender,"ví gửi"),font_name=FONT_REGULAR))
        rcpt=tx_data.get('to','N/A')
        if rcpt!='N/A':menu_layout.add_widget(Button(text="Copy ví nhận",on_press=lambda x:copy_and_dismiss(rcpt,"ví nhận"),font_name=FONT_REGULAR))
        tx_hash=tx_data.get('tx_hash','N/A')
        if tx_hash!='N/A':menu_layout.add_widget(Button(text="Copy mã GD",on_press=lambda x:copy_and_dismiss(tx_hash,"mã giao dịch"),font_name=FONT_REGULAR))
        menu_layout.add_widget(Button(text="Đóng",on_press=popup.dismiss,background_color=get_color_from_hex("#bdc3c7"),font_name=FONT_BOLD));popup.add_widget(menu_layout);popup.open()

class WebsiteScreen(BaseScreen):
    #... (Mã giữ nguyên)
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        main_layout=BoxLayout(orientation='vertical',padding=20,spacing=20);add_card=Card(height=200,size_hint_y=None);add_card.add_widget(ThemedLabel(text="Quản lý Website",font_size='20sp',font_name=FONT_BOLD,color=PRIMARY_ACCENT));self.url_input=ThemedTextInput(hint_text="Nhập URL website (vd: https://my-site.com)",size_hint_y=None,height=44);self.add_button=AppButton(text="Thêm Website",background_color=get_color_from_hex("#16a085"));self.add_button.bind(on_press=self.add_new_website);add_card.add_widget(self.url_input);add_card.add_widget(self.add_button);list_card=BoxLayout(orientation='vertical',spacing=10);list_header=BoxLayout(size_hint_y=None,height=50);list_header.add_widget(ThemedLabel(text="Các Website của bạn",font_size='20sp',font_name=FONT_BOLD));self.refresh_button=AppButton(text="Làm mới",size_hint_x=None,width=120);self.refresh_button.bind(on_press=lambda x:self.refresh_websites(x));list_header.add_widget(self.refresh_button);scroll=ScrollView(size_hint=(1,1),bar_width=0);self.website_grid=GridLayout(cols=1,spacing=10,size_hint_y=None);self.website_grid.bind(minimum_height=self.website_grid.setter('height'));scroll.add_widget(self.website_grid);list_card.add_widget(list_header);list_card.add_widget(scroll);main_layout.add_widget(add_card);main_layout.add_widget(list_card);self.add_widget(main_layout)
    def on_enter(self,*args):self.refresh_websites(self.refresh_button)
    def add_new_website(self,instance):
        url=self.url_input.text.strip()
        if not url:self.app.show_popup("Lỗi","Vui lòng nhập URL của website.");return
        instance.disabled=True;instance.text="Đang thêm..."
        threading.Thread(target=self._add_website_thread,args=(url,instance),daemon=True).start()
    def _add_website_thread(self,url,btn_instance):
        result=self.backend.add_website(url)
        def _callback(dt):
            if result and 'error' not in result:
                self.app.show_popup("Thành công",f"Đã gửi yêu cầu thêm website:\n{url[:40]}...")
                self.refresh_websites(self.refresh_button);self.url_input.text=""
            else:self.app.show_popup("Lỗi", (result or {}).get('error', "Không thể thêm website."))
            btn_instance.disabled=False;btn_instance.text="Thêm Website"
        Clock.schedule_once(_callback)
    def fund_website_popup(self, url_to_fund):
        content=BoxLayout(orientation='vertical',padding=20,spacing=10);popup=ModalView(size_hint=(0.8,None),height=300,background_color=(1,1,1,0.95));content.add_widget(Label(text=f"Nạp tiền cho:\n{url_to_fund[:30]}...",font_size='18sp',color=TEXT_COLOR_DARK,font_name=FONT_BOLD));amount_input=TextInput(hint_text="Nhập số SOK để nạp",input_filter='float',multiline=False,font_name=FONT_REGULAR,foreground_color=TEXT_COLOR_DARK,background_color=(.9,.9,.9,1));content.add_widget(amount_input);buttons=BoxLayout(size_hint_y=None,height=50,spacing=10);confirm_btn=Button(text="Xác nhận Nạp",background_color=get_color_from_hex("#27ae60"),font_name=FONT_BOLD);cancel_btn=Button(text="Hủy",font_name=FONT_REGULAR);buttons.add_widget(confirm_btn);buttons.add_widget(cancel_btn);content.add_widget(buttons)
        def do_fund(*args):
            popup.dismiss();amount_str=amount_input.text.strip()
            if not amount_str:self.app.show_popup("Lỗi","Vui lòng nhập số tiền.");return
            threading.Thread(target=self._fund_website_thread,args=(amount_str,),daemon=True).start()
        confirm_btn.bind(on_press=do_fund);cancel_btn.bind(on_press=popup.dismiss);popup.add_widget(content);popup.open()
    def _fund_website_thread(self,amount):
        result=self.backend.send_transaction(self.backend.treasury_address,amount)
        if result and 'error' not in result:
            msg,title="Đã gửi yêu cầu nạp tiền thành công.","Thành công"
            Clock.schedule_once(lambda dt:self.refresh_websites(self.refresh_button))
        else:msg,title=(result or{}).get('error',"Gửi thất bại."),"Lỗi"
        Clock.schedule_once(lambda dt:self.app.show_popup(title,msg))
    def refresh_websites(self,instance):instance.disabled=True;instance.text="Tải...";threading.Thread(target=self._fetch_websites_thread,args=(instance,),daemon=True).start()
    def _fetch_websites_thread(self,btn_instance):websites=self.backend.list_my_websites();Clock.schedule_once(lambda dt:self.populate_website_list(websites,btn_instance))
    def populate_website_list(self,websites,btn_instance):
        self.website_grid.clear_widgets()
        if websites is None or (isinstance(websites,dict) and'error'in websites):self.website_grid.add_widget(ThemedLabel(text=f"Lỗi tải danh sách: {(websites or {}).get('error','')}"))
        elif not websites:self.website_grid.add_widget(ThemedLabel(text="Bạn chưa thêm website nào."))
        else:
            for site in websites:self.website_grid.add_widget(self.create_website_card(site))
        btn_instance.disabled=False;btn_instance.text="Làm mới"
    def create_website_card(self,site_data):
        card=Card(height=120,size_hint_y=None,padding=[15,15],spacing=10);main_box=BoxLayout(orientation='horizontal');info_box=BoxLayout(orientation='vertical');url_text=site_data.get('url','N/A');site_info=site_data.get('info',{});funded=float(site_info.get('views_funded','0'));completed=float(site_info.get('views_completed','0'));url_label=ThemedLabel(text=f"[b]URL:[/b] {url_text}",markup=True,halign='left',font_name=FONT_BOLD);funded_label=ThemedLabel(text=f"Lượt xem đã nạp: [b]{funded:,.0f}[/b]",markup=True,color=get_color_from_hex("#3498db"),halign='left');completed_label=ThemedLabel(text=f"Lượt xem hoàn thành: {completed:,.0f}",markup=True,color=get_color_from_hex("#2ecc71"),halign='left');[l.bind(size=l.setter('text_size'))for l in[url_label,funded_label,completed_label]];info_box.add_widget(url_label);info_box.add_widget(funded_label);info_box.add_widget(completed_label);actions_box=BoxLayout(orientation='vertical',size_hint_x=0.3,spacing=5);fund_btn=Button(text="Nạp",background_color=get_color_from_hex("#1abc9c"),font_name=FONT_BOLD);fund_btn.bind(on_press=lambda x,u=url_text:self.fund_website_popup(u));remove_btn=Button(text="Xoá",background_color=get_color_from_hex("#c0392b"),font_name=FONT_BOLD);remove_btn.bind(on_press=lambda x,u=url_text:self.confirm_remove_website(u));actions_box.add_widget(fund_btn);actions_box.add_widget(remove_btn);main_box.add_widget(info_box);main_box.add_widget(actions_box);card.add_widget(main_box);return card
    def confirm_remove_website(self,url_to_remove):
        if not url_to_remove or url_to_remove=='N/A':self.app.show_popup("Lỗi","Không thể xóa website không hợp lệ.");return
        content=BoxLayout(orientation='vertical',padding=20,spacing=10);popup=ModalView(size_hint=(0.8,None),height=250);content.add_widget(Label(text="Xác nhận Xóa",font_size='20sp',color=TEXT_COLOR_DARK,font_name=FONT_BOLD));content.add_widget(Label(text=f"Bạn có chắc muốn xóa:\n{url_to_remove}?",text_size=(Window.width*0.7,None),color=TEXT_COLOR_DARK,font_name=FONT_REGULAR));buttons=BoxLayout(size_hint_y=None,height=50,spacing=10);confirm_btn=Button(text="Xóa",background_color=get_color_from_hex("#c0392b"),font_name=FONT_BOLD);cancel_btn=Button(text="Hủy",font_name=FONT_REGULAR);buttons.add_widget(confirm_btn);buttons.add_widget(cancel_btn);content.add_widget(buttons)
        def do_remove(*args):popup.dismiss();threading.Thread(target=self._remove_website_thread,args=(url_to_remove,),daemon=True).start()
        confirm_btn.bind(on_press=do_remove);cancel_btn.bind(on_press=popup.dismiss);popup.add_widget(content);popup.open()
    def _remove_website_thread(self,url):
        result=self.backend.remove_website(url)
        if result and 'error' not in result:msg,title=result.get('message',"Đã xóa thành công"),"Thành công";Clock.schedule_once(lambda dt:self.refresh_websites(self.refresh_button))
        else:msg,title=(result or{}).get('error',"Không thể xóa."),"Thất bại"
        Clock.schedule_once(lambda dt:self.app.show_popup(title,msg))

class MinerScreen(BaseScreen):
    #... (Mã giữ nguyên)
    scale=NumericProperty(1.0)
    ADDRESS_BOOK_FILE='address_book.json'
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self.address_book_path=os.path.join(self.app.user_data_dir,self.ADDRESS_BOOK_FILE)
        root_scroll=ScrollView(bar_width=0);main_layout=BoxLayout(orientation='vertical',padding=20,spacing=20,size_hint_y=None);main_layout.bind(minimum_height=main_layout.setter('height'))
        miner_card=Card(size_hint_y=None,height=350);
        miner_card.add_widget(ThemedLabel(text="Thợ Mỏ",font_size='24sp',font_name=FONT_BOLD,color=PRIMARY_ACCENT))
        self.icon_container = FloatLayout(size_hint_y=None, height=100)
        self.stopped_icon = ThemedLabel(text="...", font_size='80sp', font_name=FONT_ICON, pos_hint={'center_x': 0.5, 'center_y': 0.5})
        self.mining_logo = Image(source=LOGO_FILE, opacity=0, pos_hint={'center_x': 0.5, 'center_y': 0.5}, size_hint=(None,None), size=(80,80))
        self.icon_container.add_widget(self.stopped_icon); self.icon_container.add_widget(self.mining_logo)
        miner_card.add_widget(self.icon_container)
        self.state_label=ThemedLabel(text="Trạng thái: STOPPED",font_size='18sp'); self.log_label=ThemedLabel(text="Log: ...",font_size='14sp',color=(.7,.7,.7,1),halign='center')
        miner_card.add_widget(self.state_label);miner_card.add_widget(self.log_label)
        miner_btns_layout=BoxLayout(orientation='horizontal',size_hint_y=None,height=50,spacing=10);start_btn=AppButton(text="Bắt đầu",background_color=get_color_from_hex("#27ae60"));stop_btn=AppButton(text="Tạm dừng",background_color=get_color_from_hex("#c0392b"));start_btn.bind(on_press=self.start_mining);stop_btn.bind(on_press=self.stop_mining);miner_btns_layout.add_widget(start_btn);miner_btns_layout.add_widget(stop_btn)
        send_card=Card(size_hint_y=None,height=250);send_card.add_widget(ThemedLabel(text="Gửi SOK",font_size='24sp',font_name=FONT_BOLD,color=PRIMARY_ACCENT));rcpt_layout=BoxLayout(size_hint_y=None,height=44);self.recipient_input=ThemedTextInput(hint_text="Địa chỉ người nhận",multiline=False);addr_book_btn=Button(text="Sổ",size_hint_x=None,width=80,font_name=FONT_BOLD);addr_book_btn.bind(on_press=self.show_address_book);rcpt_layout.add_widget(self.recipient_input);rcpt_layout.add_widget(addr_book_btn);self.amount_input=ThemedTextInput(hint_text="Số lượng SOK",multiline=False,input_filter='float',size_hint_y=None,height=44);send_btn=AppButton(text="Gửi",background_color=get_color_from_hex("#3498db"));send_btn.bind(on_press=self.send_sok);send_card.add_widget(rcpt_layout);send_card.add_widget(self.amount_input);send_card.add_widget(send_btn)
        main_layout.add_widget(miner_card);main_layout.add_widget(miner_btns_layout);main_layout.add_widget(send_card);root_scroll.add_widget(main_layout);self.add_widget(root_scroll)
    def start_breathing_effect(self):Animation.cancel_all(self,'scale');anim=Animation(scale=1.15,duration=1.5)+Animation(scale=1.0,duration=1.5);anim.repeat=True;anim.start(self)
    def stop_breathing_effect(self):Animation.cancel_all(self,'scale');Animation(scale=1.0,duration=0.2).start(self)
    def on_scale(self,instance,value):
        target_widget = self.mining_logo
        if hasattr(target_widget, 'canvas'):
            target_widget.canvas.before.clear();
            with target_widget.canvas.before:PushMatrix();Scale(value,value,1,origin=target_widget.center)
            target_widget.canvas.after.clear();
            with target_widget.canvas.after:PopMatrix()
    def on_enter(self,*args):
        if self.backend:
            self.backend.log_callback=self.update_miner_ui
            status=self.backend.get_miner_status()
            self.update_miner_ui(status.get('state','STOPPED'),status.get('last_log','...'))
    def start_mining(self,instance):
        if self.backend:success,msg=self.backend.start_miner();self.app.show_popup("Thông báo",msg)
    def stop_mining(self,instance):
        if self.backend:success,msg=self.backend.stop_miner();self.app.show_popup("Thông báo",msg)
    def update_miner_ui(self,state,message):Clock.schedule_once(lambda dt:self._update_labels_and_nav(state,message))
    def _update_labels_and_nav(self,state,message):
        self.state_label.text=f"Trạng thái: {state}";self.log_label.text=f"Log: {message}"
        active_states=["MINING","SUCCESS","NODE_SWITCHED","SEARCHING","STARTING"]
        is_active=state in active_states
        if is_active:
            self.mining_logo.opacity = 1; self.stopped_icon.opacity = 0; self.start_breathing_effect()
        else:
            self.mining_logo.opacity = 0; self.stopped_icon.opacity = 1; self.stop_breathing_effect()
        try:
            miner_btn=self.app.miner_nav_button
            active_color,default_color=get_color_from_hex("#27ae60"),PRIMARY_ACCENT
            target_color=active_color if is_active else default_color
            if miner_btn.color != target_color: miner_btn.color = target_color
        except AttributeError:pass
    def load_address_book(self):
        if os.path.exists(self.address_book_path):
            try:
                with open(self.address_book_path,'r',encoding='utf-8')as f:return json.load(f)
            except(json.JSONDecodeError,FileNotFoundError):return[]
        return[]
    def save_address_book(self,addresses):
        with open(self.address_book_path,'w',encoding='utf-8')as f:json.dump(addresses,f,indent=2)
    def add_to_address_book(self,address):
        addresses=self.load_address_book()
        if address not in addresses:addresses.insert(0,address);self.save_address_book(addresses)
    def show_address_book(self,instance):
        addresses=self.load_address_book();content=BoxLayout(orientation='vertical',padding=10,spacing=10);popup=ModalView(size_hint=(0.9,0.8));content.add_widget(Label(text="Sổ địa chỉ",size_hint_y=None,height=40,font_size='20sp',color=TEXT_COLOR_DARK,font_name=FONT_BOLD));scroll=ScrollView();grid=GridLayout(cols=1,size_hint_y=None,spacing=5);grid.bind(minimum_height=grid.setter('height'))
        if not addresses:grid.add_widget(Label(text="Chưa có địa chỉ nào.",color=TEXT_COLOR_DARK,font_name=FONT_REGULAR))
        else:
            for addr in addresses:
                btn=Button(text=f"{addr[:20]}...\n...{addr[-20:]}",size_hint_y=None,height=60,halign='center',font_name=FONT_REGULAR)
                btn.bind(on_press=lambda x,a=addr:self.select_address(a,popup));grid.add_widget(btn)
        scroll.add_widget(grid);content.add_widget(scroll);close_btn=Button(text="Đóng",size_hint_y=None,height=50,font_name=FONT_BOLD);close_btn.bind(on_press=popup.dismiss);content.add_widget(close_btn);popup.add_widget(content);popup.open()
    def select_address(self,address,popup):self.recipient_input.text=address;popup.dismiss()
    def send_sok(self,instance):
        rcpt=self.recipient_input.text.strip();amount=self.amount_input.text.strip()
        if not rcpt or not amount:self.app.show_popup("Lỗi","Vui lòng nhập đủ thông tin.");return
        instance.disabled=True;instance.text="Đang gửi..."
        threading.Thread(target=self._send_thread,args=(rcpt,amount,instance),daemon=True).start()
    def _send_thread(self,rcpt,amount,btn_instance):
        result=self.backend.send_transaction(rcpt,amount)
        def _callback(dt):
            if result and 'error' not in result:
                msg,title=result.get('message',"Gửi thành công!"),"Thành công"
                self.add_to_address_book(rcpt);self.clear_inputs()
            else:msg,title=(result or{}).get('error',"Gửi thất bại."),"Thất bại"
            self.app.show_popup(title,msg);self.reset_button(btn_instance)
        Clock.schedule_once(_callback)
    def clear_inputs(self):self.recipient_input.text,self.amount_input.text="",""
    def reset_button(self,instance):instance.disabled,instance.text=False,"Gửi"

class MainScreen(Screen):
    #... (Mã giữ nguyên)
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app=App.get_running_app();main_layout=BoxLayout(orientation='vertical')
        header=BoxLayout(size_hint_y=None,height=70,padding=(15,15));logo=Image(source=LOGO_FILE,size_hint_x=None,width=150,allow_stretch=True,keep_ratio=True);header.add_widget(logo);header.add_widget(Widget())
        self.sm=ScreenManager(transition=SlideTransition(direction='left',duration=0.2));self.sm.add_widget(DashboardScreen(name='dashboard'));self.sm.add_widget(HistoryScreen(name='history'));self.sm.add_widget(WebsiteScreen(name='website'));self.sm.add_widget(MinerScreen(name='miner'))
        nav_layout=GridLayout(cols=4,size_hint_y=None,height=60);buttons={"Bảng tin":"dashboard","Lịch sử":"history","Website":"website","Khai thác":"miner"}
        for text,screen_name in buttons.items():
            btn=Button(text=text,background_color=(0,0,0,0),font_name=FONT_BOLD,color=PRIMARY_ACCENT,font_size='14sp')
            btn.bind(on_press=lambda i,s=screen_name:setattr(self.sm,'current',s));nav_layout.add_widget(btn)
            if screen_name=='miner':self.app.miner_nav_button=btn
        main_layout.add_widget(header);main_layout.add_widget(self.sm);main_layout.add_widget(nav_layout);self.add_widget(main_layout)

# --- Màn hình Manager (Thêm nút "Nhập ví") ---
class ManagerScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.main_container=FloatLayout();self.add_widget(self.main_container)
        
        # Bố cục tạo ví
        self.create_layout=BoxLayout(orientation='vertical',size_hint=(.9,None),pos_hint={'center_x':.5,'center_y':.5},spacing=10); self.create_layout.bind(height=self.create_layout.setter('height'))
        card_create=Card();card_create.add_widget(ThemedLabel(text="Chào mừng!",font_size='24sp',font_name=FONT_BOLD));self.new_pass_input=ThemedTextInput(hint_text="Nhập mật khẩu mới",password=True,size_hint_y=None,height=44);self.confirm_pass_input=ThemedTextInput(hint_text="Xác nhận mật khẩu",password=True,size_hint_y=None,height=44);create_btn=AppButton(text="Tạo Ví");create_btn.bind(on_press=self.create_wallet);card_create.add_widget(self.new_pass_input);card_create.add_widget(self.confirm_pass_input);card_create.add_widget(create_btn)
        
        # [MỚI] Nút Import
        import_btn = Button(text="Hoặc, Nhập từ Private Key", size_hint_y=None, height=40, background_color=(0,0,0,0), font_name=FONT_REGULAR, underline=True); import_btn.bind(on_press=self.app.show_import_popup)
        card_create.add_widget(import_btn)
        self.create_layout.add_widget(card_create)
        
        # Bố cục đăng nhập
        self.login_layout=BoxLayout(orientation='vertical',size_hint=(.9,None),pos_hint={'center_x':.5,'center_y':.5},height=220,spacing=10);card_login=Card();card_login.add_widget(ThemedLabel(text="Mở khóa Ví",font_size='24sp',font_name=FONT_BOLD));self.pass_input=ThemedTextInput(hint_text="Nhập mật khẩu",password=True,size_hint_y=None,height=44);login_btn=AppButton(text="Mở khóa");login_btn.bind(on_press=self.login);card_login.add_widget(self.pass_input);card_login.add_widget(login_btn);self.login_layout.add_widget(card_login)

    # Các hàm còn lại của ManagerScreen
    def on_enter(self,*args):
        self.main_container.clear_widgets()
        if self.backend.does_wallet_exist():self.main_container.add_widget(self.login_layout)
        else:self.main_container.add_widget(self.create_layout)
    def create_wallet(self,instance):
        pwd=self.new_pass_input.text;confirm_pwd=self.confirm_pass_input.text
        if not pwd or pwd!=confirm_pwd:self.app.show_popup("Lỗi","Mật khẩu không khớp hoặc bị bỏ trống.");return
        instance.disabled=True;instance.text="Đang tạo..."
        threading.Thread(target=self._create_wallet_thread,args=(pwd,instance),daemon=True).start()
    def _create_wallet_thread(self,pwd,btn_instance):
        success,result=self.backend.create_new_wallet(pwd)
        def _callback(dt):
            btn_instance.disabled=False;btn_instance.text="Tạo Ví"
            if success:self.app.show_backup_popup(result)
            else:self.app.show_popup("Lỗi tạo ví",result)
        Clock.schedule_once(_callback)
    def login(self,instance):
        pwd=self.pass_input.text
        if not pwd:self.app.show_popup("Lỗi","Vui lòng nhập mật khẩu.");return
        instance.disabled=True;instance.text="Đang mở..."
        threading.Thread(target=self._login_thread,args=(pwd,instance),daemon=True).start()
    def _login_thread(self,pwd,btn_instance):
        success,msg=self.backend.load_wallet_from_file(pwd)
        def _callback(dt):
            btn_instance.disabled=False;btn_instance.text="Mở khóa"
            if success:
                if self.app.backend.server_url:self.manager.current='main'
                else:self.app.show_popup("Thông báo","Mở ví thành công!\nGiờ hãy kết nối đến server.")
            else:self.app.show_popup("Lỗi đăng nhập",msg)
        Clock.schedule_once(_callback)

class SokKivyApp(App):
    def build(self):
        self.title='SOK Chain Wallet';self.icon=ICON_FILE;Window.clearcolor=(0,0,0,1)
        self.backend=BackendLogic(app_data_dir=self.user_data_dir,log_callback=self.miner_log_callback)
        root=FloatLayout();root.add_widget(AuroraBackground())
        self.sm=ScreenManager(transition=NoTransition());self.sm.add_widget(ManagerScreen(name='manager'));self.sm.add_widget(MainScreen(name='main'))
        root.add_widget(self.sm)
        Clock.schedule_once(lambda dt: self.show_server_connect_popup())
        return root
    def miner_log_callback(self, state, message):
        try:
            main_screen = self.sm.get_screen('main')
            miner_screen = main_screen.sm.get_screen('miner')
            miner_screen.update_miner_ui(state, message)
        except Exception: pass
    def show_server_connect_popup(self):
        content=BoxLayout(orientation='vertical',padding=20,spacing=10);popup=ModalView(size_hint=(0.8,None),height=250,auto_dismiss=False)
        content.add_widget(Label(text="Kết nối Server",font_size='20sp',color=TEXT_COLOR_DARK,font_name=FONT_BOLD))
        self.ip_input=TextInput(text="127.0.0.1",hint_text="Nhập IP server",multiline=False,font_name=FONT_REGULAR,foreground_color=TEXT_COLOR_DARK,background_color=(.9,.9,.9,1))
        content.add_widget(self.ip_input)
        connect_btn=Button(text="Kết nối",size_hint_y=None,height=50,font_name=FONT_BOLD)
        content.add_widget(connect_btn)
        def do_connect(*args):
            connect_btn.disabled=True;connect_btn.text="Đang kết nối..."
            ip_addr=self.ip_input.text.strip()
            threading.Thread(target=self._connect_to_server_thread,args=(ip_addr,popup,connect_btn),daemon=True).start()
        connect_btn.bind(on_press=do_connect);popup.add_widget(content);popup.open()
    def _connect_to_server_thread(self,ip,popup,btn):
        success,msg=self.backend.connect_to_server(ip)
        def _callback(dt):
            if success:popup.dismiss()
            else:self.show_popup("Lỗi Kết Nối",msg);btn.disabled=False;btn.text="Kết nối"
        Clock.schedule_once(_callback)
    def show_popup(self,title,message):
        content=BoxLayout(orientation='vertical',padding=20,spacing=10);content.add_widget(Label(text=title,font_size='18sp',bold=True,color=TEXT_COLOR_DARK,font_name=FONT_BOLD));content.add_widget(Label(text=message,color=TEXT_COLOR_DARK,text_size=(Window.width*0.7,None),font_name=FONT_REGULAR));close_btn=Button(text="Đóng",size_hint_y=None,height=50,font_name=FONT_BOLD);content.add_widget(close_btn);popup=ModalView(size_hint=(0.8,None),size_hint_max_y=0.8,height=300,background_color=(1,1,1,0.95));popup.add_widget(content);close_btn.bind(on_press=popup.dismiss);popup.open()
    
    # [THAY ĐỔI] Thêm tham số `is_creation` để tùy chỉnh nút bấm
    def show_backup_popup(self, private_key, is_creation=True):
        def on_dismiss(*args):
            if is_creation:
                # Sau khi tạo mới, quay lại màn hình manager để đăng nhập
                self.sm.get_screen('manager').on_enter()
        
        content=BoxLayout(orientation='vertical',padding=10,spacing=10);
        content.add_widget(Label(text="SAO LƯU KEY NÀY CẨN THẬN!",bold=True,size_hint_y=None,height=40,color=TEXT_COLOR_DARK,font_name=FONT_BOLD))
        scroll=ScrollView(size_hint_y=0.8);
        scroll.add_widget(TextInput(text=private_key,readonly=True,size_hint_y=None,height=250,font_name=FONT_REGULAR,foreground_color=TEXT_COLOR_DARK,background_color=(.9,.9,.9,1)))
        content.add_widget(scroll)

        button_text = "Tôi đã sao lưu, đến màn hình đăng nhập" if is_creation else "Tôi đã sao lưu, đóng"
        close_btn = Button(text=button_text, size_hint_y=None, height=50, font_name=FONT_BOLD)
        content.add_widget(close_btn)

        popup=ModalView(size_hint=(0.9,0.7),auto_dismiss=False,background_color=(1,1,1,0.95));popup.add_widget(content)
        close_btn.bind(on_press=popup.dismiss)
        if is_creation:
            popup.bind(on_dismiss=on_dismiss)
        popup.open()
    
    # [MỚI] Popup để nhập ví
    def show_import_popup(self, instance):
        content=BoxLayout(orientation='vertical',padding=20,spacing=10);popup=ModalView(size_hint=(0.9,0.9),background_color=(1,1,1,0.95))
        content.add_widget(Label(text="Nhập từ Private Key",font_size='20sp',color=TEXT_COLOR_DARK,font_name=FONT_BOLD))
        key_input = TextInput(hint_text="Dán Private Key PEM của bạn vào đây", size_hint_y=0.5, font_name=FONT_REGULAR, foreground_color=TEXT_COLOR_DARK, background_color=(.9,.9,.9,1))
        pass_input = TextInput(hint_text="Tạo mật khẩu MỚI cho thiết bị này", password=True, multiline=False, foreground_color=TEXT_COLOR_DARK, background_color=(.9,.9,.9,1))
        confirm_pass_input = TextInput(hint_text="Xác nhận mật khẩu MỚI", password=True, multiline=False, foreground_color=TEXT_COLOR_DARK, background_color=(.9,.9,.9,1))
        import_btn = Button(text="Nhập Ví", size_hint_y=None, height=50, font_name=FONT_BOLD)
        
        content.add_widget(key_input); content.add_widget(pass_input); content.add_widget(confirm_pass_input); content.add_widget(import_btn)
        
        def do_import(*args):
            pem = key_input.text.strip()
            pwd = pass_input.text
            confirm_pwd = confirm_pass_input.text
            if not pem or not pwd or not confirm_pwd:
                self.show_popup("Lỗi", "Vui lòng điền đầy đủ thông tin.")
                return
            if pwd != confirm_pwd:
                self.show_popup("Lỗi", "Mật khẩu không khớp.")
                return
            
            import_btn.disabled = True; import_btn.text = "Đang nhập..."
            threading.Thread(target=self._import_thread, args=(pem, pwd, popup, import_btn), daemon=True).start()

        import_btn.bind(on_press=do_import)
        popup.add_widget(content)
        popup.open()
        
    def _import_thread(self, pem, pwd, popup, btn):
        success, msg = self.backend.import_wallet_from_pem(pem, pwd)
        def _callback(dt):
            if success:
                popup.dismiss()
                self.show_popup("Thành Công", "Ví của bạn đã được nhập và bảo vệ.\nHãy đăng nhập bằng mật khẩu mới.")
                self.sm.get_screen('manager').on_enter() # Refresh để hiện màn hình login
            else:
                self.show_popup("Lỗi Nhập Ví", msg)
                btn.disabled = False; btn.text = "Nhập Ví"
        Clock.schedule_once(_callback)

    def on_stop(self):
        if hasattr(self,'backend'):self.backend.shutdown()

if __name__=='__main__':
    SokKivyApp().run()
