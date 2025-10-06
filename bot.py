import discord
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import asyncio
import aiohttp
import json
import random
import time
import yt_dlp
from discord import FFmpegPCMAudio, FFmpegOpusAudio

# Загружаем переменные окружения
load_dotenv()

# Настройка бота
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents, case_insensitive=True)

# Русские фразы для бота
PHRASES = {
    'ready': 'Бот готов к работе!',
    'hello': 'Привет! Как дела? 😊',
    'goodbye': 'До свидания! Удачи! 👋',
    'help': '''🤖 **Что я умею:**

**📋 Основные команды:**
• `!помощь` - показать эту справку
• `!время` - показать текущее время
• `!привет` / `!hello` - поздороваться
• `!пока` / `!bye` - попрощаться

**🌤️ Погода:**
• `!погода` - прогноз для основных городов
• `!погода <город>` - прогноз для любого города

**💰 Криптовалюты:**
• `!крипта` - основные криптовалюты
• `!крипта <символ>` - конкретная криптовалюта

**🎲 Рандом:**
• `!poll <число>` - случайное число от 1 до указанного
• `!рандом <число>` - то же самое на русском

**🎵 Музыка и радио:**
• `!join` / `!подключиться` - подключиться к голосовому каналу
• `!radio` / `!радио` - включить радио
• `!stop` / `!стоп` - остановить воспроизведение
• `!leave` / `!отключиться` - отключиться от канала

**🔴 Twitch мониторинг (только админы):**
• `!twitch добавить <канал>` - подписаться на уведомления
• `!twitch удалить <канал>` - отписаться от уведомлений
• `!twitch список` - показать подписки

**⚙️ Управление каналами (только админы):**
• `!канал добавить` - разрешить боту работать в канале
• `!канал удалить` - запретить боту работать в канале
• `!канал список` - показать разрешенные каналы

**🔧 Диагностика (только админы):**
• `!тест` - проверить работу API
• `!кэш` - показать статистику кэша
• `!обновить` - очистить кэш''',
    'time': 'Текущее время: ',
    'unknown': 'Извините, я не понимаю эту команду. Напишите `!помощь` для списка команд.',
    'error': 'Произошла ошибка при выполнении команды.',
    'weather_error': 'Не удалось получить данные о погоде. Проверьте API ключ.',
    'no_api_key': 'API ключ OpenWeatherMap не настроен.'
}

# Города для прогноза погоды
CITIES = {
    'Москва': {'lat': 55.7558, 'lon': 37.6176, 'flag': '🇷🇺'},
    'Краснодар': {'lat': 45.0355, 'lon': 38.9753, 'flag': '🇷🇺'},
    'Киев': {'lat': 50.4501, 'lon': 30.5234, 'flag': '🇺🇦'},
    'Львов': {'lat': 49.838, 'lon': 24.023, 'flag': '🇺🇦'}
}

# Сокращения популярных городов
CITY_SHORTCUTS = {
    'спб': 'Санкт-Петербург',
    'питер': 'Санкт-Петербург',
    'екб': 'Екатеринбург',
    'мск': 'Москва'
}

# Эмодзи для погодных условий
WEATHER_EMOJIS = {
    'ясно': '☀️',
    'малооблачно': '⛅',
    'переменная облачность': '☁️',
    'облачно': '☁️',
    'пасмурно': '☁️',
    'небольшой дождь': '🌦️',
    'дождь': '🌧️',
    'сильный дождь': '🌧️',
    'ливень': '🌧️',
    'небольшой снег': '🌨️',
    'снег': '❄️',
    'сильный снег': '❄️',
    'туман': '🌫️',
    'гроза': '⛈️',
    'морось': '🌦️'
}

# Хранилище для отслеживания Twitch каналов
TWITCH_SUBSCRIPTIONS = {}
TWITCH_ACCESS_TOKEN = None

# Хранилище для разрешенных каналов
ALLOWED_CHANNELS = {}

# Хранилище для голосовых подключений
voice_clients = {}

# Криптовалюты для мониторинга
CRYPTO_SYMBOLS = {
    'btc': 'bitcoin',
    'eth': 'ethereum', 
    'usdt': 'tether',
    'bnb': 'binancecoin',
    'xrp': 'ripple',
    'ada': 'cardano',
    'doge': 'dogecoin',
    'sol': 'solana',
    'link': 'chainlink',
    'ltc': 'litecoin'
}

# Кэш для криптовалют
crypto_cache = {}

@bot.event
async def on_ready():
    """Событие готовности бота"""
    print(f'{PHRASES["ready"]} Вошел как {bot.user}')
    
    # Устанавливаем статус бота
    activity = discord.Game(name="!помощь")
    await bot.change_presence(activity=activity)
    
    # Запускаем мониторинг Twitch стримов
    if not check_twitch_streams.is_running():
        check_twitch_streams.start()
        print("🔴 Мониторинг Twitch стримов запущен")

# ===== ОСНОВНЫЕ КОМАНДЫ =====

@bot.command(name='помощь')
async def help_command(ctx):
    """Показать справку"""
    embed = discord.Embed(
        title="🤖 Справка по командам",
        description=PHRASES['help'],
        color=0x00ff00
    )
    await ctx.reply(embed=embed)

@bot.command(name='время', aliases=['time'])
async def current_time(ctx):
    """Показать текущее время"""
    try:
        now = datetime.now()
        time_str = now.strftime('%d %B %Y, %H:%M:%S')
        
        # Переводим месяцы на русский
        months = {
            'January': 'января', 'February': 'февраля', 'March': 'марта',
            'April': 'апреля', 'May': 'мая', 'June': 'июня',
            'July': 'июля', 'August': 'августа', 'September': 'сентября',
            'October': 'октября', 'November': 'ноября', 'December': 'декабря'
        }
        
        for eng, rus in months.items():
            time_str = time_str.replace(eng, rus)
            
        await ctx.reply(f"{PHRASES['time']}{time_str}")
    except Exception as e:
        await ctx.reply(PHRASES['error'])
        print(f"Ошибка в команде время: {e}")

@bot.command(name='привет', aliases=['hello'])
async def hello(ctx):
    """Поздороваться с ботом"""
    await ctx.reply(PHRASES['hello'])

@bot.command(name='пока', aliases=['bye'])
async def goodbye(ctx):
    """Попрощаться с ботом"""
    await ctx.reply(PHRASES['goodbye'])

# ===== КОМАНДЫ РАНДОМА =====

@bot.command(name='poll', aliases=['рандом'])
async def poll_command(ctx, max_number: int = None):
    """Выбрать случайное число от 1 до указанного"""
    if max_number is None:
        await ctx.reply("❌ Укажите максимальное число! Пример: `!poll 100`")
        return
    
    if max_number < 1:
        await ctx.reply("❌ Число должно быть больше 0!")
        return
    
    if max_number > 1000000:
        await ctx.reply("❌ Число слишком большое! Максимум 1,000,000")
        return
    
    result = random.randint(1, max_number)
    await ctx.reply(f"🎲 Случайное число от 1 до {max_number}: **{result}**")

# ===== МУЗЫКАЛЬНЫЕ КОМАНДЫ =====

@bot.command(name='join', aliases=['подключиться'])
async def join_voice(ctx):
    """Подключиться к голосовому каналу"""
    if not ctx.author.voice:
        await ctx.reply("❌ Вы не подключены к голосовому каналу!")
        return
    
    channel = ctx.author.voice.channel
    
    try:
        voice_client = await channel.connect()
        voice_clients[ctx.guild.id] = voice_client
        await ctx.reply(f"✅ Подключился к каналу **{channel.name}**")
    except Exception as e:
        await ctx.reply(f"❌ Ошибка подключения: {str(e)}")

@bot.command(name='leave', aliases=['отключиться'])
async def leave_voice(ctx):
    """Отключиться от голосового канала"""
    if ctx.guild.id in voice_clients:
        await voice_clients[ctx.guild.id].disconnect()
        del voice_clients[ctx.guild.id]
        await ctx.reply("✅ Отключился от голосового канала")
    else:
        await ctx.reply("❌ Я не подключен к голосовому каналу")

@bot.command(name='stop', aliases=['стоп'])
async def stop_music(ctx):
    """Остановить воспроизведение"""
    if ctx.guild.id in voice_clients:
        voice_client = voice_clients[ctx.guild.id]
        if voice_client.is_playing():
            voice_client.stop()
            await ctx.reply("⏹️ Воспроизведение остановлено")
        else:
            await ctx.reply("❌ Ничего не воспроизводится")
    else:
        await ctx.reply("❌ Ничего не воспроизводится")

@bot.command(name='radio', aliases=['радио'])
async def play_radio(ctx):
    """Включить радио"""
    if not ctx.author.voice:
        await ctx.reply("❌ Вы не подключены к голосовому каналу!")
        return
    
    # Подключаемся к каналу если не подключены
    if ctx.guild.id not in voice_clients:
        try:
            voice_client = await ctx.author.voice.channel.connect()
            voice_clients[ctx.guild.id] = voice_client
        except Exception as e:
            await ctx.reply(f"❌ Ошибка подключения: {str(e)}")
            return
    
    voice_client = voice_clients[ctx.guild.id]
    
    # Останавливаем текущее воспроизведение
    if voice_client.is_playing():
        voice_client.stop()
        await asyncio.sleep(2)
    
    try:
        # Используем простую и надежную радиостанцию
        radio_url = "http://stream.radiorecord.ru:8102/rr_320"
        
        # ПРАВИЛЬНЫЕ настройки для Discord - это критично!
        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin',
            'options': '-vn -f s16le -ar 48000 -ac 2 -loglevel panic'
        }
        
        await ctx.send("🔄 Подключаюсь к Radio Record...")
        
        # Создаем источник аудио с правильными настройками
        source = FFmpegPCMAudio(radio_url, **ffmpeg_options)
        
        # Запускаем воспроизведение
        voice_client.play(source, after=lambda e: print(f'Player error: {e}') if e else None)
        
        # Ждем стабилизации потока
        await asyncio.sleep(3)
        
        if voice_client.is_playing():
            embed = discord.Embed(
                title="📻 Радио включено!",
                description="Воспроизводится: **Radio Record**",
                color=0x00ff00
            )
            embed.add_field(name="Статус", value="🔴 В эфире", inline=True)
            embed.add_field(name="Качество", value="320 kbps", inline=True)
            embed.add_field(name="Формат", value="PCM 48kHz", inline=True)
            
            await ctx.reply(embed=embed)
        else:
            await ctx.reply("❌ Не удалось запустить воспроизведение. Попробуйте `!radio_fix`")
            
    except Exception as e:
        await ctx.reply(f"❌ Ошибка воспроизведения: {str(e)}")
        print(f"Radio error: {e}")

@bot.command(name='radio_fix', aliases=['радио_фикс'])
async def radio_fix(ctx):
    """Альтернативная команда радио с FFmpegOpusAudio"""
    if not ctx.author.voice:
        await ctx.reply("❌ Вы не подключены к голосовому каналу!")
        return
    
    # Подключаемся к каналу если не подключены
    if ctx.guild.id not in voice_clients:
        try:
            voice_client = await ctx.author.voice.channel.connect()
            voice_clients[ctx.guild.id] = voice_client
        except Exception as e:
            await ctx.reply(f"❌ Ошибка подключения: {str(e)}")
            return
    
    voice_client = voice_clients[ctx.guild.id]
    
    # Останавливаем текущее воспроизведение
    if voice_client.is_playing():
        voice_client.stop()
        await asyncio.sleep(2)
    
    try:
        radio_url = "http://stream.radiorecord.ru:8102/rr_320"
        
        # Пробуем FFmpegOpusAudio вместо FFmpegPCMAudio
        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin',
            'options': '-vn'
        }
        
        await ctx.send("🔄 Пробую Opus кодек...")
        
        # Используем FFmpegOpusAudio для лучшей совместимости с Discord
        source = FFmpegOpusAudio(radio_url, **ffmpeg_options)
        
        voice_client.play(source, after=lambda e: print(f'Opus Player error: {e}') if e else None)
        
        await asyncio.sleep(3)
        
        if voice_client.is_playing():
            embed = discord.Embed(
                title="📻 Радио включено! (Opus)",
                description="Воспроизводится: **Radio Record**",
                color=0x00ff00
            )
            embed.add_field(name="Кодек", value="Opus", inline=True)
            embed.add_field(name="Статус", value="🔴 В эфире", inline=True)
            
            await ctx.reply(embed=embed)
        else:
            await ctx.reply("❌ Opus кодек тоже не работает. Проверьте настройки FFmpeg.")
            
    except Exception as e:
        await ctx.reply(f"❌ Ошибка с Opus: {str(e)}")
        print(f"Opus error: {e}")

@bot.command(name='radio_debug', aliases=['радио_дебуг'])
async def radio_debug(ctx):
    """Детальная диагностика радио с разными настройками FFmpeg"""
    if not ctx.author.voice:
        await ctx.reply("❌ Вы не подключены к голосовому каналу!")
        return
    
    # Подключаемся к каналу если не подключены
    if ctx.guild.id not in voice_clients:
        try:
            voice_client = await ctx.author.voice.channel.connect()
            voice_clients[ctx.guild.id] = voice_client
        except Exception as e:
            await ctx.reply(f"❌ Ошибка подключения: {str(e)}")
            return
    
    voice_client = voice_clients[ctx.guild.id]
    
    # Тестовая станция
    test_url = "http://stream.radiorecord.ru:8102/rr_320"
    
    # Разные варианты настроек FFmpeg
    ffmpeg_variants = [
        {
            'name': 'Стандартные настройки',
            'options': {
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin',
                'options': '-vn'
            }
        },
        {
            'name': 'PCM 48kHz',
            'options': {
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin',
                'options': '-vn -acodec pcm_s16le -ar 48000 -ac 2'
            }
        },
        {
            'name': 'Opus кодек',
            'options': {
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin',
                'options': '-vn -acodec libopus -ar 48000 -ac 2 -b:a 128k'
            }
        },
        {
            'name': 'Простой MP3',
            'options': {
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin',
                'options': '-vn -ar 48000 -ac 2 -b:a 128k'
            }
        }
    ]
    
    embed = discord.Embed(title="🔧 Диагностика радио", color=0x0099ff)
    
    for variant in ffmpeg_variants:
        try:
            # Останавливаем предыдущее воспроизведение
            if voice_client.is_playing():
                voice_client.stop()
                await asyncio.sleep(2)
            
            await ctx.send(f"🔄 Тестирую: **{variant['name']}**")
            
            source = FFmpegPCMAudio(test_url, **variant['options'])
            voice_client.play(source)
            
            # Ждем дольше для стабилизации
            await asyncio.sleep(5)
            
            if voice_client.is_playing():
                embed.add_field(
                    name=f"✅ {variant['name']}", 
                    value="Воспроизводится успешно", 
                    inline=False
                )
                # Оставляем играть эту версию если она работает
                break
            else:
                embed.add_field(
                    name=f"❌ {variant['name']}", 
                    value="Не воспроизводится", 
                    inline=False
                )
                
        except Exception as e:
            embed.add_field(
                name=f"❌ {variant['name']}", 
                value=f"Ошибка: {str(e)[:100]}", 
                inline=False
            )
    
    await ctx.reply(embed=embed)

@bot.command(name='radio_test', aliases=['радио_тест'])
async def radio_test(ctx):
    """Тестирование радиостанций"""
    if not ctx.author.voice:
        await ctx.reply("❌ Вы не подключены к голосовому каналу!")
        return
    
    # Подключаемся к каналу если не подключены
    if ctx.guild.id not in voice_clients:
        try:
            voice_client = await ctx.author.voice.channel.connect()
            voice_clients[ctx.guild.id] = voice_client
        except Exception as e:
            await ctx.reply(f"❌ Ошибка подключения: {str(e)}")
            return
    
    voice_client = voice_clients[ctx.guild.id]
    
    # Тестовые радиостанции
    test_stations = [
        {
            'name': 'Test Stream 1',
            'url': 'http://stream.radiorecord.ru:8102/rr_320'
        },
        {
            'name': 'Test Stream 2', 
            'url': 'http://icecast.vgtrk.cdnvideo.ru/mayakfm_mp3_192kbps'
        },
        {
            'name': 'Test Stream 3',
            'url': 'http://pub0202.101.ru:8000/stream/air/aac/64/102'
        }
    ]
    
    embed = discord.Embed(title="🔧 Тест радиостанций", color=0x0099ff)
    
    for station in test_stations:
        try:
            # Останавливаем предыдущее воспроизведение
            if voice_client.is_playing():
                voice_client.stop()
                await asyncio.sleep(1)
            
            # Простые настройки FFmpeg для теста
            ffmpeg_options = {
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin',
                'options': '-vn'
            }
            
            source = FFmpegPCMAudio(station['url'], **ffmpeg_options)
            voice_client.play(source)
            
            # Ждем и проверяем
            await asyncio.sleep(3)
            
            if voice_client.is_playing():
                embed.add_field(
                    name=f"✅ {station['name']}", 
                    value=f"Работает\n`{station['url']}`", 
                    inline=False
                )
                voice_client.stop()
            else:
                embed.add_field(
                    name=f"❌ {station['name']}", 
                    value=f"Не работает\n`{station['url']}`", 
                    inline=False
                )
                
        except Exception as e:
            embed.add_field(
                name=f"❌ {station['name']}", 
                value=f"Ошибка: {str(e)[:100]}\n`{station['url']}`", 
                inline=False
            )
    
    await ctx.reply(embed=embed)

# ===== КОМАНДЫ ПОГОДЫ =====

@bot.command(name='погода', aliases=['weather'])
async def weather(ctx, *, city_name=None):
    """Показать прогноз погоды на 2 дня для городов или конкретного города"""
    api_key = os.getenv('OPENWEATHER_API_KEY')
    if not api_key:
        await ctx.reply(PHRASES['no_api_key'])
        return
    
    try:
        if city_name:
            # Проверяем сокращения городов
            original_city_name = city_name
            city_name_lower = city_name.lower()
            
            if city_name_lower in CITY_SHORTCUTS:
                city_name = CITY_SHORTCUTS[city_name_lower]
                display_name = f"{city_name} ({original_city_name})"
            else:
                display_name = city_name.title()
            
            # Поиск погоды для конкретного города
            weather_data = await get_weather_by_city_name(api_key, city_name)
            if weather_data:
                embed = discord.Embed(
                    title=f"🌤️ Прогноз погоды для города {display_name}",
                    color=0x87CEEB
                )
                
                city_info = format_weather_for_city(display_name, weather_data, '🌍')
                embed.add_field(
                    name=f"🌍 **{display_name.upper()}**",
                    value=city_info,
                    inline=False
                )
                
                embed.set_footer(text="Данные предоставлены OpenWeatherMap")
                await ctx.reply(embed=embed)
            else:
                await ctx.reply(f"❌ Не удалось найти город '{original_city_name}'. Проверьте правильность написания.")
        else:
            # Показать погоду для основных городов
            embed = discord.Embed(
                title="🌤️ Прогноз погоды на 2 дня",
                color=0x87CEEB
            )
            
            for city_name, coords in CITIES.items():
                weather_data = await get_weather_forecast(api_key, coords['lat'], coords['lon'])
                if weather_data:
                    city_info = format_weather_for_city(city_name, weather_data, coords['flag'])
                    embed.add_field(
                        name=f"🌍 **{city_name.upper()}** {coords['flag']}",
                        value=city_info,
                        inline=False
                    )
            
            embed.set_footer(text="Данные предоставлены OpenWeatherMap • !погода <город> для поиска погоды в вашем городе")
            await ctx.reply(embed=embed)
        
    except Exception as e:
        await ctx.reply(PHRASES['weather_error'])
        print(f"Ошибка в команде погода: {e}")

async def get_weather_forecast(api_key, lat, lon):
    """Получить прогноз погоды через OpenWeatherMap API"""
    url = f"http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=ru"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            return None

async def get_weather_by_city_name(api_key, city_name):
    """Получить прогноз погоды по названию города"""
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={city_name}&appid={api_key}&units=metric&lang=ru"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            return None

def format_weather_for_city(city_name, weather_data, flag):
    """Форматировать данные о погоде для города"""
    if not weather_data or 'list' not in weather_data:
        return "❌ Данные недоступны"
    
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)
    
    today_forecasts = []
    tomorrow_forecasts = []
    
    # Собираем все прогнозы для каждого дня
    for item in weather_data['list']:
        forecast_date = datetime.fromtimestamp(item['dt']).date()
        
        if forecast_date == today:
            today_forecasts.append(item)
        elif forecast_date == tomorrow:
            tomorrow_forecasts.append(item)
    
    result = ""
    
    # Сегодня
    if today_forecasts:
        min_temp = min(round(item['main']['temp_min']) for item in today_forecasts)
        max_temp = max(round(item['main']['temp_max']) for item in today_forecasts)
        
        # Берем самое частое описание погоды за день
        descriptions = [item['weather'][0]['description'] for item in today_forecasts]
        most_common_desc = max(set(descriptions), key=descriptions.count)
        
        # Добавляем эмодзи к описанию
        emoji = ""
        for key, value in WEATHER_EMOJIS.items():
            if key in most_common_desc.lower():
                emoji = value
                break
        
        # Средняя скорость ветра за день
        avg_wind = round(sum(item['wind']['speed'] for item in today_forecasts) / len(today_forecasts), 1)
        
        result += f"📅 **Сегодня**\n"
        result += f"🌡️ **{min_temp}°C** ... **{max_temp}°C**  "
        result += f"**|**  {emoji} {most_common_desc.capitalize()}\n"
        result += f"💨 Ветер: **{avg_wind} м/с**\n"
    
    # Завтра
    if tomorrow_forecasts:
        min_temp = min(round(item['main']['temp_min']) for item in tomorrow_forecasts)
        max_temp = max(round(item['main']['temp_max']) for item in tomorrow_forecasts)
        
        # Берем самое частое описание погоды за день
        descriptions = [item['weather'][0]['description'] for item in tomorrow_forecasts]
        most_common_desc = max(set(descriptions), key=descriptions.count)
        
        # Добавляем эмодзи к описанию
        emoji = ""
        for key, value in WEATHER_EMOJIS.items():
            if key in most_common_desc.lower():
                emoji = value
                break
        
        # Средняя скорость ветра за день
        avg_wind = round(sum(item['wind']['speed'] for item in tomorrow_forecasts) / len(tomorrow_forecasts), 1)
        
        result += f"\n📅 **Завтра**\n"
        result += f"🌡️ **{min_temp}°C** ... **{max_temp}°C**  "
        result += f"**|**  {emoji}  {most_common_desc.capitalize()} \n"
        result += f"💨 Ветер: **{avg_wind} м/с**\n"
    
    return result if result else "❌ Данные недоступны"

# ===== КОМАНДЫ КРИПТОВАЛЮТ =====

@bot.command(name='крипта', aliases=['crypto'])
async def crypto_command(ctx, *symbols):
    """Показать информацию о криптовалютах"""
    try:
        if not symbols:
            # Показать основные криптовалюты
            symbols = ['btc', 'eth', 'usdt', 'bnb']
        
        crypto_data = await get_crypto_data(symbols)
        
        if not crypto_data:
            await ctx.reply("❌ Не удалось получить данные о криптовалютах")
            return
        
        embed = discord.Embed(
            title="💰 Криптовалюты",
            color=0xFFD700
        )
        
        for symbol, data in crypto_data.items():
            if 'link_only' in data:
                continue
                
            price = data.get('usd', 0)
            change_24h = data.get('usd_24h_change', 0)
            
            # Форматируем цену
            if price >= 1:
                price_str = f"${price:,.2f}"
            else:
                price_str = f"${price:.6f}"
            
            # Форматируем изменение
            change_emoji = "📈" if change_24h >= 0 else "📉"
            change_str = f"{change_24h:+.2f}%"
            
            embed.add_field(
                name=f"{symbol.upper()}",
                value=f"{price_str}\n{change_emoji} {change_str}",
                inline=True
            )
        
        embed.set_footer(text="Данные предоставлены CoinPaprika")
        await ctx.reply(embed=embed)
        
    except Exception as e:
        await ctx.reply("❌ Ошибка при получении данных о криптовалютах")
        print(f"Ошибка в команде крипта: {e}")

async def get_crypto_data(symbols):
    """Получить данные о криптовалютах через CoinPaprika API с кэшированием"""
    if isinstance(symbols, str):
        symbols = [symbols]
    
    results = {}
    now = time.time()
    
    for symbol in symbols:
        symbol_lower = symbol.lower()
        
        # Проверяем кэш для криптовалют
        cache_key = f"crypto_{symbol_lower}"
        if cache_key in crypto_cache:
            cached_data, last_updated = crypto_cache[cache_key]
            # Если прошло меньше 60 секунд - используем кэш
            if now - last_updated < 60:
                results[symbol_lower] = cached_data
                continue
        
        # Получаем данные из API
        coin_data = await fetch_coinpaprika_data(symbol_lower)
        if coin_data:
            # Сохраняем в кэш
            crypto_cache[cache_key] = (coin_data, now)
            results[symbol_lower] = coin_data
    
    return results if results else None

async def fetch_coinpaprika_data(symbol):
    """Получить данные монеты из CoinPaprika API"""
    try:
        # Сначала получаем ID монеты по символу
        coin_id = await get_coinpaprika_id(symbol)
        if not coin_id:
            return None
        
        # Получаем данные о цене
        url = f"https://api.coinpaprika.com/v1/tickers/{coin_id}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Форматируем данные под наш формат
                    quotes = data.get('quotes', {}).get('USD', {})
                    return {
                        'usd': quotes.get('price', 0),
                        'usd_24h_change': quotes.get('percent_change_24h', 0),
                        'usd_market_cap': quotes.get('market_cap', 0),
                        'original_symbol': symbol
                    }
                else:
                    print(f"CoinPaprika API error {response.status} for {symbol}")
                    return None
                    
    except Exception as e:
        print(f"Ошибка при получении данных CoinPaprika для {symbol}: {e}")
        return None

async def get_coinpaprika_id(symbol):
    """Получить ID монеты в CoinPaprika по символу"""
    symbol_lower = symbol.lower()
    
    # Маппинг популярных символов на CoinPaprika ID
    coinpaprika_ids = {
        'btc': 'btc-bitcoin',
        'eth': 'eth-ethereum',
        'usdt': 'usdt-tether',
        'bnb': 'bnb-binance-coin',
        'xrp': 'xrp-xrp',
        'ada': 'ada-cardano',
        'doge': 'doge-dogecoin',
        'sol': 'sol-solana',
        'link': 'link-chainlink',
        'ltc': 'ltc-litecoin'
    }
    
    if symbol_lower in coinpaprika_ids:
        return coinpaprika_ids[symbol_lower]
    
    return None

# ===== TWITCH КОМАНДЫ =====

# Twitch API функции
async def get_twitch_access_token():
    """Получить токен доступа к Twitch API"""
    client_id = os.getenv('TWITCH_CLIENT_ID')
    client_secret = os.getenv('TWITCH_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        return None
    
    url = 'https://id.twitch.tv/oauth2/token'
    params = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials'
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data.get('access_token')
    return None

async def check_twitch_stream(channel_name):
    """Проверить статус стрима на Twitch"""
    global TWITCH_ACCESS_TOKEN
    
    if not TWITCH_ACCESS_TOKEN:
        TWITCH_ACCESS_TOKEN = await get_twitch_access_token()
        if not TWITCH_ACCESS_TOKEN:
            return None
    
    client_id = os.getenv('TWITCH_CLIENT_ID')
    headers = {
        'Client-ID': client_id,
        'Authorization': f'Bearer {TWITCH_ACCESS_TOKEN}'
    }
    
    url = f'https://api.twitch.tv/helix/streams?user_login={channel_name}'
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return data.get('data', [])
            elif response.status == 401:  # Токен истек
                TWITCH_ACCESS_TOKEN = await get_twitch_access_token()
                return await check_twitch_stream(channel_name)
    return None

@tasks.loop(minutes=2)
async def check_twitch_streams():
    """Проверять статус всех отслеживаемых стримов каждые 2 минуты"""
    for guild_id, channels in TWITCH_SUBSCRIPTIONS.items():
        guild = bot.get_guild(guild_id)
        if not guild:
            continue
            
        for channel_name, info in channels.items():
            try:
                stream_data = await check_twitch_stream(channel_name)
                
                if stream_data and len(stream_data) > 0:
                    # Стрим онлайн
                    if not info['is_live']:
                        # Стрим только что начался
                        info['is_live'] = True
                        
                        discord_channel = guild.get_channel(info['channel_id'])
                        if discord_channel:
                            message = info.get('message', f"Поток {channel_name} потёк! 🔴")
                            
                            embed = discord.Embed(
                                title="🔴 Стрим начался!",
                                description=message,
                                color=0x9146FF,
                                url=f"https://twitch.tv/{channel_name}"
                            )
                            
                            stream_info = stream_data[0]
                            embed.add_field(name="Канал", value=channel_name, inline=True)
                            embed.add_field(name="Игра", value=stream_info.get('game_name', 'Не указана'), inline=True)
                            embed.add_field(name="Зрители", value=stream_info.get('viewer_count', 0), inline=True)
                            embed.add_field(name="Название", value=stream_info.get('title', 'Без названия'), inline=False)
                            
                            await discord_channel.send(embed=embed)
                else:
                    # Стрим оффлайн
                    info['is_live'] = False
                    
            except Exception as e:
                print(f"Ошибка при проверке стрима {channel_name}: {e}")

@bot.group(name='twitch', invoke_without_command=True)
async def twitch_group(ctx):
    """Группа команд для управления Twitch уведомлениями"""
    await ctx.send("Используйте `!twitch добавить <канал>`, `!twitch удалить <канал>` или `!twitch список`")

def extract_channel_name(input_text):
    """Извлечь имя канала из ссылки или текста"""
    input_text = input_text.strip()
    
    if 'twitch.tv/' in input_text:
        channel_name = input_text.split('twitch.tv/')[-1]
        channel_name = channel_name.split('?')[0]
        channel_name = channel_name.rstrip('/')
        return channel_name.lower()
    
    return input_text.lower()

@twitch_group.command(name='добавить', aliases=['add'])
@commands.has_permissions(administrator=True)
async def twitch_add(ctx, *, channel_input: str):
    """Добавить Twitch канал для мониторинга"""
    guild_id = ctx.guild.id
    
    if guild_id not in TWITCH_SUBSCRIPTIONS:
        TWITCH_SUBSCRIPTIONS[guild_id] = {}
    
    channel_name = extract_channel_name(channel_input)
    
    if not channel_name:
        await ctx.reply("❌ Не удалось определить имя канала.")
        return
    
    # Проверяем, существует ли канал на Twitch
    stream_data = await check_twitch_stream(channel_name)
    if stream_data is None:
        await ctx.reply(f"❌ Не удалось найти канал '{channel_name}' на Twitch.")
        return
    
    TWITCH_SUBSCRIPTIONS[guild_id][channel_name] = {
        'channel_id': ctx.channel.id,
        'message': f"Поток {channel_name} потёк! 🔴",
        'is_live': len(stream_data) > 0
    }
    
    await ctx.reply(f"✅ Канал '{channel_name}' добавлен для мониторинга!")

@twitch_group.command(name='удалить', aliases=['remove'])
@commands.has_permissions(administrator=True)
async def twitch_remove(ctx, *, channel_input: str):
    """Удалить Twitch канал из мониторинга"""
    guild_id = ctx.guild.id
    channel_name = extract_channel_name(channel_input)
    
    if guild_id in TWITCH_SUBSCRIPTIONS and channel_name in TWITCH_SUBSCRIPTIONS[guild_id]:
        del TWITCH_SUBSCRIPTIONS[guild_id][channel_name]
        await ctx.reply(f"✅ Канал '{channel_name}' удален из мониторинга.")
    else:
        await ctx.reply(f"❌ Канал '{channel_name}' не найден в списке мониторинга.")

@twitch_group.command(name='список', aliases=['list'])
async def twitch_list(ctx):
    """Показать список отслеживаемых каналов"""
    guild_id = ctx.guild.id
    
    if guild_id not in TWITCH_SUBSCRIPTIONS or not TWITCH_SUBSCRIPTIONS[guild_id]:
        await ctx.reply("📋 Нет отслеживаемых каналов.")
        return
    
    embed = discord.Embed(
        title="📋 Отслеживаемые Twitch каналы",
        color=0x9146FF
    )
    
    for channel_name, info in TWITCH_SUBSCRIPTIONS[guild_id].items():
        status = "🔴 В эфире" if info['is_live'] else "⚫ Не в эфире"
        discord_channel = ctx.guild.get_channel(info['channel_id'])
        channel_mention = discord_channel.mention if discord_channel else "Канал удален"
        
        embed.add_field(
            name=f"{channel_name} {status}",
            value=f"Канал: {channel_mention}",
            inline=False
        )
    
    await ctx.reply(embed=embed)

# ===== АДМИНИСТРАТИВНЫЕ КОМАНДЫ =====

@bot.group(name='канал', aliases=['channel'], invoke_without_command=True)
async def channel_group(ctx):
    """Группа команд для управления разрешенными каналами"""
    await ctx.send("Используйте `!канал добавить`, `!канал удалить`, `!канал список` или `!канал сброс`")

@channel_group.command(name='добавить', aliases=['add'])
@commands.has_permissions(administrator=True)
async def channel_add(ctx):
    """Разрешить боту работать в текущем канале"""
    guild_id = ctx.guild.id
    channel_id = ctx.channel.id
    
    if guild_id not in ALLOWED_CHANNELS:
        ALLOWED_CHANNELS[guild_id] = []
    
    if channel_id not in ALLOWED_CHANNELS[guild_id]:
        ALLOWED_CHANNELS[guild_id].append(channel_id)
        await ctx.reply(f"✅ Канал {ctx.channel.mention} добавлен в список разрешенных")
    else:
        await ctx.reply(f"❌ Канал {ctx.channel.mention} уже в списке разрешенных")

@channel_group.command(name='удалить', aliases=['remove'])
@commands.has_permissions(administrator=True)
async def channel_remove(ctx):
    """Запретить боту работать в текущем канале"""
    guild_id = ctx.guild.id
    channel_id = ctx.channel.id
    
    if guild_id in ALLOWED_CHANNELS and channel_id in ALLOWED_CHANNELS[guild_id]:
        ALLOWED_CHANNELS[guild_id].remove(channel_id)
        await ctx.reply(f"✅ Канал {ctx.channel.mention} удален из списка разрешенных")
    else:
        await ctx.reply(f"❌ Канал {ctx.channel.mention} не найден в списке разрешенных")

@channel_group.command(name='список', aliases=['list'])
async def channel_list(ctx):
    """Показать список разрешенных каналов"""
    guild_id = ctx.guild.id
    
    if guild_id not in ALLOWED_CHANNELS or not ALLOWED_CHANNELS[guild_id]:
        await ctx.reply("📋 Все каналы разрешены (список пуст)")
        return
    
    channels = []
    for channel_id in ALLOWED_CHANNELS[guild_id]:
        channel = ctx.guild.get_channel(channel_id)
        if channel:
            channels.append(channel.mention)
        else:
            channels.append(f"Удаленный канал (ID: {channel_id})")
    
    embed = discord.Embed(
        title="📋 Разрешенные каналы",
        description="\n".join(channels),
        color=0x00ff00
    )
    await ctx.reply(embed=embed)

@channel_group.command(name='сброс', aliases=['reset'])
@commands.has_permissions(administrator=True)
async def channel_reset(ctx):
    """Разрешить работу во всех каналах"""
    guild_id = ctx.guild.id
    
    if guild_id in ALLOWED_CHANNELS:
        del ALLOWED_CHANNELS[guild_id]
    
    await ctx.reply("✅ Список разрешенных каналов очищен. Бот теперь работает во всех каналах")

# ===== ДИАГНОСТИЧЕСКИЕ КОМАНДЫ =====

@bot.command(name='тест')
@commands.has_permissions(administrator=True)
async def test_apis(ctx):
    """Проверить работу API"""
    embed = discord.Embed(title="🔧 Тест API", color=0x00ff00)
    
    # Тест OpenWeatherMap
    weather_key = os.getenv('OPENWEATHER_API_KEY')
    if weather_key:
        try:
            async with aiohttp.ClientSession() as session:
                url = f"http://api.openweathermap.org/data/2.5/weather?q=Moscow&appid={weather_key}"
                async with session.get(url) as response:
                    if response.status == 200:
                        embed.add_field(name="🌤️ OpenWeatherMap", value="✅ Работает", inline=True)
                    else:
                        embed.add_field(name="🌤️ OpenWeatherMap", value="❌ Ошибка", inline=True)
        except:
            embed.add_field(name="🌤️ OpenWeatherMap", value="❌ Ошибка", inline=True)
    else:
        embed.add_field(name="🌤️ OpenWeatherMap", value="❌ Нет ключа", inline=True)
    
    # Тест CoinPaprika
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://api.coinpaprika.com/v1/tickers/btc-bitcoin"
            async with session.get(url) as response:
                if response.status == 200:
                    embed.add_field(name="💰 CoinPaprika", value="✅ Работает", inline=True)
                else:
                    embed.add_field(name="💰 CoinPaprika", value="❌ Ошибка", inline=True)
    except:
        embed.add_field(name="💰 CoinPaprika", value="❌ Ошибка", inline=True)
    
    # Тест Twitch
    twitch_id = os.getenv('TWITCH_CLIENT_ID')
    twitch_secret = os.getenv('TWITCH_CLIENT_SECRET')
    if twitch_id and twitch_secret:
        token = await get_twitch_access_token()
        if token:
            embed.add_field(name="🔴 Twitch", value="✅ Работает", inline=True)
        else:
            embed.add_field(name="🔴 Twitch", value="❌ Ошибка", inline=True)
    else:
        embed.add_field(name="🔴 Twitch", value="❌ Нет ключей", inline=True)
    
    await ctx.reply(embed=embed)

@bot.command(name='кэш')
@commands.has_permissions(administrator=True)
async def cache_info(ctx):
    """Показать информацию о кэше"""
    embed = discord.Embed(title="📊 Статистика кэша", color=0x0099ff)
    embed.add_field(name="Записей в кэше", value=len(crypto_cache), inline=True)
    await ctx.reply(embed=embed)

@bot.command(name='обновить')
@commands.has_permissions(administrator=True)
async def refresh_cache(ctx):
    """Очистить кэш"""
    old_size = len(crypto_cache)
    crypto_cache.clear()
    await ctx.reply(f"🔄 Кэш очищен! Удалено {old_size} записей.")

# ===== ЗАПУСК БОТА =====

if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("Ошибка: DISCORD_TOKEN не найден в .env файле!")
    else:
        try:
            bot.run(token)
        except Exception as e:
            print(f"Ошибка запуска бота: {e}")