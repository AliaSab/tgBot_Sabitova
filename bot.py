import time
import datetime
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from bs4 import BeautifulSoup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import Group_Number
import removeDates


API_TOKEN = '7239307458:AAHKbE4yXSPf02MayCx4O7ZZFB__Bywdg9o'
CHAT_ID = '1349323472' 

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)  
dp = Dispatcher()  

# Настройки для браузера Edge
options = Options()
options.add_argument('--ignore-certificate-errors')  # Игнорировать ошибки сертификата

# Функция для получения расписания для заданной группы
def get_schedule(group):
    driver = webdriver.Edge(service=Service(EdgeChromiumDriverManager().install()), options=options)  # Инициализация WebDriver для Edge
           
    schedule = []  # Список для хранения расписания
    try:
        driver.get("https://kpfu.ru/studentu/ucheba/raspisanie")  # Переход на страницу с расписанием
        time.sleep(5)  # Ожидание загрузки страницы

        # ввод группы
        input_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'p_group_name'))
        )
        input_field.send_keys(group)

        # нажатие кнопки
        button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(@style, 'but_show.png')]"))
        )
        button.click()
        time.sleep(5)

        html_content = driver.page_source  # Получение HTML-кода страницы
        soup = BeautifulSoup(html_content, 'html.parser')  

        # Поиск таблиц с расписанием
        for table in soup.find_all('table'):
            if 'font-size:14px' in str(table):  # Печать нужного таблицы по стилю
                header_row = table.find('tr')  # Первая строка с заголовками
                headers = [header.text.strip() for header in header_row.find_all('td') if header.text.strip()]

                for row in table.find_all('tr')[1:]:  # Пропустить заголовок
                    time_cell = row.find('td') 
                    time_value = time_cell.text.strip() if time_cell else "Время не указано"  
                    daily_classes = [time_value]  

                    for day_cell in row.find_all('td')[1:]:
                        class_info = day_cell.text.strip() if day_cell else " "
                        class_info = removeDates.remove_dates(class_info)
                        class_info = removeDates.remove_dates(class_info)  # Удаление дат
                        daily_classes.append(class_info)  # Добавление информации о предмете

                    schedule.append(daily_classes)  # Добавление списка занятий в расписание
                return headers, schedule  # Возвращение заголовков и расписания
        return None, None

    except Exception as e:
        logging.error(f"Ошибка при получении расписания: {e}") 
        return None, None 
    finally:
        driver.quit() 

# преобразование названия дня недели в индекс
def day_of_week_to_index(day: str) -> int:
    days = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота"]
    day = day.lower().strip()  
    if day in days:
        return days.index(day)  
    return -1  

# Обработка команды "/start"
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Расписание на день", callback_data='daily_schedule'),
            InlineKeyboardButton(text="Расписание на неделю", callback_data='weekly_schedule'),
        ]
    ])
    await message.answer("Добро пожаловать! Выберите, что хотите сделать:", reply_markup=keyboard)

# Обработка нажатий на инлайн-кнопки
@dp.callback_query()
async def handle_callback(call: types.CallbackQuery):
    if call.data == 'daily_schedule':
        await call.answer("Введите день (например, понедельник) и номер группы (например, 09-402).")
        await call.message.reply("Формат: <день> <номер группы>.")
    elif call.data == 'weekly_schedule':
        await call.answer("Введите номер группы (например, 09-402) для получения расписания на неделю.")
        await call.message.reply("Формат: <номер группы>.")

# Обработка сообщений, содержащих расписание
@dp.message()
async def cmd_schedule(message: types.Message):
    # Обработка расписания на день
    if ' ' in message.text:  # Предполагаем, что введен день и группа
        args = message.text.split()  
        if len(args) == 2:  
            day_of_week = args[0]  # день
            group = args[1]  # группа
            day_index = day_of_week_to_index(day_of_week)
            if day_index == -1:
                await message.answer("Введите корректный день недели: понедельник, вторник, среда, четверг, пятница, суббота.")
                return 
            
            if group not in Group_Number.groups:
                await bot.send_message(message.chat.id, "Такой группы нет.")
                return

            # Вычисление даты для указанного дня
            today = datetime.datetime.now()
            day_difference = (day_index - today.weekday()) % 7 
            target_date = today + datetime.timedelta(days=day_difference)  
            formatted_date = target_date.strftime("%d.%m.%Y") 

            headers, schedule = get_schedule(group)  

            if headers is None: 
                await bot.send_message(message.chat.id, "Не удалось получить расписание.")
                return

            response = f"Расписание на <b>{day_of_week.capitalize()} ({formatted_date})</b> для группы {group}:\n"

            has_classes = False  # Флаг наличия занятий

            for class_row in schedule:
                time_slot = class_row[0]  # Время текущего занятия

                if len(class_row) > day_index + 1 and class_row[day_index + 1]:  
                    subject = class_row[day_index + 1]  
                    response += f"⏰ {time_slot} \n {subject} \n"  
                    has_classes = True 

            if not has_classes:
                response += "Занятий нет."  

            await bot.send_message(message.chat.id, response, parse_mode='HTML')

    # Обработка расписания на неделю
    else:  # Если введена только группа
        group = message.text  # номер группы
        headers, schedule = get_schedule(group) 

        if headers is None:  
            await bot.send_message(message.chat.id, "Не удалось получить расписание.")
            return
        
        if group not in Group_Number.groups:
            await bot.send_message(message.chat.id, "Такой группы нет.")
            return

        response = f"<b>Расписание на неделю для группы {group}:</b>\n"

        today = datetime.datetime.now()  # Получаем текущую дату
        days_map = {
            0: 'понедельник',
            1: 'вторник',
            2: 'среда',
            3: 'четверг',
            4: 'пятница',
            5: 'суббота'
        }

        for day_index in range(6):
            day_name = days_map[day_index]  # Получаем название дня
            day_difference = (day_index - today.weekday()) % 7  
            target_date = today + datetime.timedelta(days=day_difference)  # Рассчитываем дату
            formatted_date = target_date.strftime("%d.%m.%Y") 

            response += f"<b>--- {day_name.title()} ({formatted_date}) ---</b>\n"  
            has_classes = False  

            for class_row in schedule:
                if len(class_row) > day_index + 1 and class_row[day_index + 1]:  
                    time_slot = class_row[0] 
                    subject = class_row[day_index + 1]  
                    response += f"⏰ {time_slot} \n {subject} \n" 
                    has_classes = True  

            if not has_classes:
                response += "Занятий нет.\n"  

        await bot.send_message(message.chat.id, response, parse_mode='HTML') 

# Асинхронная функция для отправки ежедневных обновлений расписания
async def schedule_daily_updates():
    while True:  
        now = datetime.datetime.now()  # текущее время
        if now.hour == 7 and now.minute == 0:   # утром
            await send_schedule(CHAT_ID, now.date(), now.weekday())  #расписание на сегодня
        if now.hour == 19 and now.minute == 0:  # вечером
            await send_schedule(CHAT_ID, now.date() + datetime.timedelta(days=1), (now + datetime.timedelta(days=1)).weekday())  # расписание на завтра
        await asyncio.sleep(60)  # Проверять каждую минуту

# Асинхронная функция для отправки расписания
async def send_schedule(chat_id, date, day_index):
    group_auto = '09-415'  
    headers, schedule = get_schedule(group_auto)  

    if headers is None: 
        await bot.send_message(chat_id, "Не удалось получить расписание.")
        return

    today_str = date.strftime('%d.%m.%Y')  # Форматируем текущую дату

    days_map = {
        0: 'понедельник',
        1: 'вторник',
        2: 'среда',
        3: 'четверг',
        4: 'пятница',
        5: 'суббота'
    }
    day_of_week = days_map[day_index]  
    response = f"--- {day_of_week.capitalize()} ({today_str}) ---\n"  
    has_classes = False 

    for class_row in schedule:
        time_slot = class_row[0]  
        if len(class_row) > day_index + 1 and class_row[day_index + 1]:  
            subject = class_row[day_index + 1] 
            response += f"⏰ {time_slot} \n {subject}\n"  
            has_classes = True  

    if not has_classes:
        response += "Занятий нет."  
    await bot.send_message(chat_id, response) 

async def main():
    asyncio.create_task(schedule_daily_updates())  # отправка ежедневных обновлений
    await dp.start_polling(bot) 

if __name__ == "__main__":
    asyncio.run(main())