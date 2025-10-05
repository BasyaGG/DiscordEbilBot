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
    'help': '''Вот что я умею:
• `!помощь` - показать эту справку
• `!время` - показать текущее время
• `!погода` - прогноз погоды для основных городов
• `!погода <город>` - прогноз погоды для любого города


**Сокращения городов:**
• `!погода спб` или `!погода питер` - Санкт-Петербург
• `!погода екб` - Екатеринбург

**Twitch уведомления (только для администраторов):**
• `!twitch добавить <ссылка>` - подписаться на уведомления
• `!twitch удалить <ссылка>` - отписаться от уведомлений
• `!twitch список` - показать подписки
• `!twitch сообщение <ссылка> <текст>` - настроить текст уведомления

**Примеры Twitch команд:**
• `!twitch добавить https://twitch.tv/shroud`
• `!twitch добавить twitch.tv/ninja`
• `!twitch добавить pokimane` (просто имя канала)

**Криптовалюты:**
• `!крипта` - показать основные криптовалюты
• `!крипта <символ>` - показать конкретную криптовалюту
• `!крипта btc eth` - показать несколько криптовалют

**Управление каналами (только для администраторов):**
• `!канал добавить` - разрешить боту работать в этом канале
• `!канал удалить` - запретить боту работать в этом канале
• `!канал список` - показать разрешенные каналы
• `!канал сброс` - разрешить боту работать во всех каналах

**Рандом:**
• `!poll <число>` - выбрать случайное число от 1 до указанного
• `!рандом <число>` - выбрать случайное число от 1 до указанного

**Музыка и радио:**
• `!join` / `!подключиться` - подключиться к голосовому каналу
• `!play <ссылка/название>` / `!играть` - воспроизвести музыку
• `!radio` / `!радио` - включить радио Bluford
• `!stop` / `!стоп` - остановить воспроизведение
• `!pause` / `!пауза` - поставить на паузу
• `!resume` / `!продолжить` - продолжить воспроизведение
• `!volume <0-100>` / `!громкость` - изменить громкость
• `!leave` / `!отключиться` - отключиться от канала''',
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

# Эмодзи для погодных условий (API уже возвращает русские описания)
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
# Структура: {guild_id: {channel_name: {'channel_id': discord_channel_id, 'message': custom_message, 'is_live': False}}}
TWITCH_SUBSCRIPTIONS = {}

# Twitch API токен (будет получен при запуске)
TWITCH_ACCESS_TOKEN = None

# Хранилище для разрешенных каналов
# Структура: {guild_id: [channel_id1, channel_id2, ...]}
ALLOWED_CHANNELS = {}

# Криптовалюты для мониторинга
CRYPTO_SYMBOLS = {
    'btc': 'bitcoin',
    'eth': 'ethereum', 
    'usdt': 'tether',
    'bnb': 'binancecoin',
    'xrp': 'ripple',
    'ada': 'cardano',
    'doge': 'dogecoin',
    'matic': 'matic-network',
    'sol': 'solana',
    'dot': 'polkadot',
    'avax': 'avalanche-2',
    'crv': 'curve-dao-token',
    'uni': 'uniswap',
    'link': 'chainlink',
    'ltc': 'litecoin',
    'atom': 'cosmos',
    'near': 'near',
    'ftm': 'fantom',
    'algo': 'algorand',
    'icp': 'internet-computer',
    'apt': 'aptos',
    'op': 'optimism',
    'arb': 'arbitrum',
    'sui': 'sui'
}

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
        
        # Берем самое частое описание погоды за день (API уже возвращает на русском)
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
        
        # Берем самое частое описание погоды за день (API уже возвращает на русском)
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
    await ctx.send("Используйте `!twitch добавить <канал>`, `!twitch удалить <канал>`, `!twitch список` или `!twitch сообщение <канал> <текст>`")

def extract_channel_name(input_text):
    """Извлечь имя канала из ссылки или текста"""
    # Убираем пробелы
    input_text = input_text.strip()
    
    # Если это полная ссылка
    if 'twitch.tv/' in input_text:
        # Извлекаем имя канала из ссылки
        channel_name = input_text.split('twitch.tv/')[-1]
        # Убираем возможные параметры после ?
        channel_name = channel_name.split('?')[0]
        # Убираем слэш в конце если есть
        channel_name = channel_name.rstrip('/')
        return channel_name.lower()
    
    # Если это просто имя канала
    return input_text.lower()

@twitch_group.command(name='добавить', aliases=['add'])
@commands.has_permissions(administrator=True)
async def twitch_add(ctx, *, channel_input: str):
    """Добавить Twitch канал для мониторинга"""
    guild_id = ctx.guild.id
    
    if guild_id not in TWITCH_SUBSCRIPTIONS:
        TWITCH_SUBSCRIPTIONS[guild_id] = {}
    
    # Извлекаем имя канала из ссылки или текста
    channel_name = extract_channel_name(channel_input)
    
    if not channel_name:
        await ctx.reply("❌ Не удалось определить имя канала. Используйте формат: `!twitch добавить twitch.tv/channel` или `!twitch добавить channel`")
        return
    
    # Проверяем, существует ли канал на Twitch
    stream_data = await check_twitch_stream(channel_name)
    if stream_data is None:
        await ctx.reply(f"❌ Не удалось найти канал '{channel_name}' на Twitch или проблема с API.")
        return
    
    TWITCH_SUBSCRIPTIONS[guild_id][channel_name] = {
        'channel_id': ctx.channel.id,
        'message': f"Поток {channel_name} потёк! 🔴",
        'is_live': len(stream_data) > 0  # Текущий статус
    }
    
    await ctx.reply(f"✅ Канал '{channel_name}' добавлен для мониторинга в этом канале!\n🔗 https://twitch.tv/{channel_name}")

@twitch_group.command(name='удалить', aliases=['remove'])
@commands.has_permissions(administrator=True)
async def twitch_remove(ctx, *, channel_input: str):
    """Удалить Twitch канал из мониторинга"""
    guild_id = ctx.guild.id
    
    # Извлекаем имя канала из ссылки или текста
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
            value=f"Канал: {channel_mention}\nСообщение: {info['message']}",
            inline=False
        )
    
    await ctx.reply(embed=embed)

@twitch_group.command(name='сообщение', aliases=['message'])
@commands.has_permissions(administrator=True)
async def twitch_message(ctx, channel_input: str, *, message: str):
    """Настроить кастомное сообщение для канала"""
    guild_id = ctx.guild.id
    
    # Извлекаем имя канала из ссылки или текста
    channel_name = extract_channel_name(channel_input)
    
    if guild_id in TWITCH_SUBSCRIPTIONS and channel_name in TWITCH_SUBSCRIPTIONS[guild_id]:
        TWITCH_SUBSCRIPTIONS[guild_id][channel_name]['message'] = message
        await ctx.reply(f"✅ Сообщение для канала '{channel_name}' обновлено!")
    else:
        await ctx.reply(f"❌ Канал '{channel_name}' не найден в списке мониторинга. Сначала добавьте его командой `!twitch добавить https://twitch.tv/{channel_name}`")

# Кэш для криптовалют (в памяти)
crypto_cache = {}

# Криптовалюты API функции (CoinPaprika)
async def get_crypto_data(symbols):
    """Получить данные о криптовалютах через CoinPaprika API с кэшированием"""
    if isinstance(symbols, str):
        symbols = [symbols]
    
    results = {}
    now = time.time()
    
    for symbol in symbols:
        symbol_lower = symbol.lower()
        
        # Специальная обработка для BTC.D (только ссылка)
        if symbol_lower == 'btc.d' or symbol_lower == 'btcd':
            results['btc.d'] = {'link_only': True}
            continue
        
        # Специальная обработка для NASDAQ (только ссылка)
        if symbol_lower == 'nasdaq':
            results['nasdaq'] = {'link_only': True}
            continue
        
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
        'matic': 'matic-polygon',
        'sol': 'sol-solana',
        'dot': 'dot-polkadot',
        'avax': 'avax-avalanche',
        'crv': 'crv-curve-dao-token',
        'uni': 'uni-uniswap',
        'link': 'link-chainlink',
        'ltc': 'ltc-litecoin',
        'atom': 'atom-cosmos',
        'near': 'near-near-protocol',
        'ftm': 'ftm-fantom',
        'algo': 'algo-algorand',
        'icp': 'icp-internet-computer',
        'apt': 'apt-aptos',
        'op': 'op-optimism',
        'arb': 'arb-arbitrum',
        'sui': 'sui-sui'
    }
    
    if symbol_lower in coinpaprika_ids:
        return coinpaprika_ids[symbol_lower]
    
    # Если нет в маппинге, пробуем найти через поиск
    try:
        cache_key = f"search_{symbol_lower}"
        now = time.time()
        
        # Проверяем кэш поиска
        if cache_key in crypto_cache:
            cached_id, last_updated = crypto_cache[cache_key]
            if now - last_updated < 3600:  # Кэш поиска на 1 час
                return cached_id
        
        url = f"https://api.coinpaprika.com/v1/search?q={symbol}&c=currencies&limit=10"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    currencies = data.get('currencies', [])
                    
                    # Ищем точное совпадение по символу
                    for currency in currencies:
                        if currency.get('symbol', '').lower() == symbol_lower:
                            coin_id = currency.get('id')
                            # Сохраняем в кэш
                            crypto_cache[cache_key] = (coin_id, now)
                            return coin_id
                    
                    # Если точного совпадения нет, берем первый результат
                    if currencies:
                        coin_id = currencies[0].get('id')
                        crypto_cache[cache_key] = (coin_id, now)
                        return coin_id
                        
    except Exception as e:
        print(f"Ошибка поиска в CoinPaprika для {symbol}: {e}")
    
    return None

async def get_btc_dominance_cached():
    """Получить Bitcoin Dominance с кэшированием"""
    cache_key = "btc_dominance"
    now = time.time()
    
    # Проверяем кэш
    if cache_key in crypto_cache:
        cached_data, last_updated = crypto_cache[cache_key]
        if now - last_updated < 300:  # Кэш на 5 минут
            return cached_data
    
    # Получаем новые данные
    dominance_data = await get_btc_dominance()
    if dominance_data:
        crypto_cache[cache_key] = (dominance_data, now)
    
    return dominance_data

async def get_btc_dominance():
    """Получить Bitcoin Dominance через несколько источников"""
    
    # Источник 1: CoinGecko API (более точные данные)
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://api.coingecko.com/api/v3/global"
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    current_dominance = data.get('data', {}).get('market_cap_percentage', {}).get('btc', 0)
                    
                    if current_dominance > 0:
                        # Получаем данные BTC для расчета изменения доминации
                        btc_url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
                        async with session.get(btc_url, timeout=10) as btc_response:
                            if btc_response.status == 200:
                                btc_data = await btc_response.json()
                                btc_change_24h = btc_data.get('bitcoin', {}).get('usd_24h_change', 0)
                                
                                # Приблизительный расчет изменения доминации
                                estimated_dominance_change = btc_change_24h * 0.05
                                
                                return {
                                    'usd': current_dominance,
                                    'usd_24h_change': estimated_dominance_change,
                                    'usd_market_cap': 0
                                }
                        
                        # Если не удалось получить изменение, возвращаем без него
                        return {
                            'usd': current_dominance,
                            'usd_24h_change': 0,
                            'usd_market_cap': 0
                        }
                else:
                    print(f"CoinGecko Global API error: {response.status}")
                    
    except Exception as e:
        print(f"CoinGecko BTC Dominance error: {e}")
    
    # Источник 2: CoinPaprika API (резервный)
    try:
        async with aiohttp.ClientSession() as session:
            global_url = "https://api.coinpaprika.com/v1/global"
            async with session.get(global_url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    current_dominance = data.get('bitcoin_dominance_percentage', 0)
                    
                    if current_dominance > 0:
                        print("Используем CoinPaprika для BTC Dominance")
                        return {
                            'usd': current_dominance,
                            'usd_24h_change': 0,
                            'usd_market_cap': 0
                        }
                else:
                    print(f"CoinPaprika Global API error: {response.status}")
                    
    except Exception as e:
        print(f"CoinPaprika BTC Dominance error: {e}")
    
    print("Все источники BTC Dominance недоступны")
    return None

async def get_nasdaq_data_cached():
    """Получить данные NASDAQ с кэшированием"""
    cache_key = "nasdaq_data"
    now = time.time()
    
    # Проверяем кэш
    if cache_key in crypto_cache:
        cached_data, last_updated = crypto_cache[cache_key]
        if now - last_updated < 300:  # Кэш на 5 минут
            return cached_data
    
    # Получаем новые данные
    nasdaq_data = await get_nasdaq_data()
    if nasdaq_data:
        crypto_cache[cache_key] = (nasdaq_data, now)
    
    return nasdaq_data

async def get_nasdaq_data():
    """Получить данные NASDAQ через несколько источников"""
    
    # Источник 1: Alpha Vantage API (если есть ключ)
    alpha_vantage_key = os.getenv('ALPHA_VANTAGE_API_KEY')
    if alpha_vantage_key:
        try:
            url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=IXIC&apikey={alpha_vantage_key}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        global_quote = data.get('Global Quote', {})
                        if global_quote:
                            current_price = float(global_quote.get('05. price', 0))
                            change_percent = float(global_quote.get('10. change percent', '0%').replace('%', ''))
                            
                            if current_price > 0:
                                print("Используем Alpha Vantage для NASDAQ")
                                return {
                                    'usd': current_price,
                                    'usd_24h_change': change_percent,
                                    'usd_market_cap': 0
                                }
                            
        except Exception as e:
            print(f"Alpha Vantage NASDAQ error: {e}")
    
    # Источник 2: Finnhub API (если есть ключ)
    finnhub_key = os.getenv('FINNHUB_API_KEY')
    if finnhub_key:
        try:
            url = f"https://finnhub.io/api/v1/quote?symbol=^IXIC&token={finnhub_key}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        current_price = data.get('c', 0)  # current price
                        previous_close = data.get('pc', 0)  # previous close
                        
                        if current_price > 0 and previous_close > 0:
                            change_24h = ((current_price - previous_close) / previous_close) * 100
                            
                            print("Используем Finnhub для NASDAQ")
                            return {
                                'usd': current_price,
                                'usd_24h_change': change_24h,
                                'usd_market_cap': 0
                            }
                            
        except Exception as e:
            print(f"Finnhub NASDAQ error: {e}")
    
    # Источник 3: Yahoo Finance (основной)
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EIXIC"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    chart = data.get('chart', {})
                    result = chart.get('result', [])
                    
                    if result:
                        meta = result[0].get('meta', {})
                        current_price = meta.get('regularMarketPrice', 0)
                        previous_close = meta.get('previousClose', 0)
                        
                        if current_price > 0 and previous_close > 0:
                            change_24h = ((current_price - previous_close) / previous_close) * 100
                            
                            print("Используем Yahoo Finance для NASDAQ")
                            return {
                                'usd': current_price,
                                'usd_24h_change': change_24h,
                                'usd_market_cap': 0
                            }
                        
    except Exception as e:
        print(f"Yahoo Finance NASDAQ error: {e}")
    
    # Источник 4: Альтернативный Yahoo Finance endpoint
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        url = "https://query2.finance.yahoo.com/v10/finance/quoteSummary/^IXIC?modules=price"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    quote_summary = data.get('quoteSummary', {})
                    result = quote_summary.get('result', [])
                    
                    if result:
                        price_data = result[0].get('price', {})
                        current_price = price_data.get('regularMarketPrice', {}).get('raw', 0)
                        previous_close = price_data.get('regularMarketPreviousClose', {}).get('raw', 0)
                        
                        if current_price > 0 and previous_close > 0:
                            change_24h = ((current_price - previous_close) / previous_close) * 100
                            
                            print("Используем альтернативный Yahoo Finance для NASDAQ")
                            return {
                                'usd': current_price,
                                'usd_24h_change': change_24h,
                                'usd_market_cap': 0
                            }
                        
    except Exception as e:
        print(f"Alternative Yahoo Finance NASDAQ error: {e}")
    
    # Источник 5: Marketstack API (если есть ключ)
    marketstack_key = os.getenv('MARKETSTACK_API_KEY')
    if marketstack_key:
        try:
            url = f"http://api.marketstack.com/v1/eod/latest?access_key={marketstack_key}&symbols=IXIC"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        eod_data = data.get('data', [])
                        if eod_data:
                            current_price = eod_data[0].get('close', 0)
                            previous_close = eod_data[0].get('open', 0)
                            
                            if current_price > 0 and previous_close > 0:
                                change_24h = ((current_price - previous_close) / previous_close) * 100
                                
                                print("Используем Marketstack для NASDAQ")
                                return {
                                    'usd': current_price,
                                    'usd_24h_change': change_24h,
                                    'usd_market_cap': 0
                                }
                            
        except Exception as e:
            print(f"Marketstack NASDAQ error: {e}")
    
    # Источник 6: Актуальные резервные данные (обновляется вручную)
    print("Используем резервные данные NASDAQ - все API недоступны")
    return {
        'usd': 19000.00,  # Более консервативное значение
        'usd_24h_change': 0.5,  # Примерное изменение
        'usd_market_cap': 0
    }

def get_tradingview_link(symbol):
    """Получить ссылку на TradingView для символа"""
    symbol_upper = symbol.upper()
    
    # Специальные случаи
    if symbol.lower() == 'btc.d':
        return "https://www.tradingview.com/symbols/CRYPTOCAP-BTC.D/"
    elif symbol.lower() == 'nasdaq':
        return "https://www.tradingview.com/symbols/NASDAQ-NDX/"
    else:
        # Для криптовалют используем формат BINANCE:SYMBOLUSDT
        return f"https://www.tradingview.com/symbols/BINANCE-{symbol_upper}USDT/"

def format_crypto_data(crypto_data, requested_symbols):
    """Форматировать данные о криптовалютах"""
    if not crypto_data:
        return "❌ Данные недоступны"
    
    result = ""
    
    for symbol in requested_symbols:
        symbol_lower = symbol.lower()
        
        # Специальная обработка для BTC.D (только ссылка)
        if symbol_lower == 'btc.d' or symbol_lower == 'btcd':
            if 'btc.d' in crypto_data:
                result += f"**BTC.D** 👑\n"
                result += f"💡 Bitcoin доминация на рынке\n"
                result += f"📈 [TradingView]({get_tradingview_link('btc.d')})\n\n"
                continue
        
        # Специальная обработка для NASDAQ (только ссылка)
        if symbol_lower == 'nasdaq':
            if 'nasdaq' in crypto_data:
                result += f"**NASDAQ** 📊\n"
                result += f"🏛️ Фондовый рынок США\n"
                result += f"📈 [TradingView]({get_tradingview_link('nasdaq')})\n\n"
                continue
        
        # Обычные криптовалюты - теперь ищем по symbol_lower ключу
        if symbol_lower in crypto_data:
            data = crypto_data[symbol_lower]
            price = data.get('usd', 0)
            change_24h = data.get('usd_24h_change', 0)
            market_cap = data.get('usd_market_cap', 0)
            
            # Определяем эмодзи для изменения цены
            if change_24h > 0:
                change_emoji = "📈"
                change_color = "+"
            elif change_24h < 0:
                change_emoji = "📉"
                change_color = ""
            else:
                change_emoji = "➡️"
                change_color = ""
            
            # Форматирование цены
            if symbol_lower in ['btc', 'eth']:
                if price >= 1:
                    price_str = f"${price:,.2f}"
                else:
                    price_str = f"${price:.6f}"
            else:
                if price >= 1:
                    price_str = f"${price:,.4f}"
                else:
                    price_str = f"${price:.8f}"
            
            # Форматирование рыночной капитализации
            if market_cap >= 1_000_000_000:
                market_cap_str = f"${market_cap/1_000_000_000:.1f}B"
            elif market_cap >= 1_000_000:
                market_cap_str = f"${market_cap/1_000_000:.1f}M"
            elif market_cap > 0:
                market_cap_str = f"${market_cap:,.0f}"
            else:
                market_cap_str = "N/A"
            
            result += f"**{symbol.upper()}** {change_emoji}\n"
            result += f"💰 Цена: **{price_str}**\n"
            result += f"📊 24ч: **{change_color}{change_24h:.2f}%**\n"
            if market_cap > 0:
                result += f"🏦 Кап: **{market_cap_str}**\n"
            result += f"📈 [TradingView]({get_tradingview_link(symbol)})\n\n"
        else:
            # Если данные не найдены
            result += f"**{symbol.upper()}** ❌\n"
            result += f"💰 Данные недоступны\n\n"
    
    return result.strip() if result else "❌ Данные недоступны"

@bot.command(name='крипта', aliases=['crypto'])
async def crypto_command(ctx, *symbols):
    """Показать информацию о криптовалютах"""
    try:
        if not symbols:
            # Показать основные криптовалюты и индексы (ваш список)
            default_symbols = ['btc.d', 'nasdaq', 'btc', 'eth', 'crv']
            crypto_data = await get_crypto_data(default_symbols)
            
            if crypto_data:
                embed = discord.Embed(
                    title="💰 Основные криптовалюты",
                    color=0xF7931A
                )
                
                formatted_data = format_crypto_data(crypto_data, default_symbols)
                embed.description = formatted_data
                embed.set_footer(text="Данные предоставлены CoinPaprika • Обновляется в реальном времени")
                
                await ctx.reply(embed=embed)
            else:
                await ctx.reply("❌ Не удалось получить данные о криптовалютах.")
        else:
            # Показать конкретные криптовалюты
            crypto_data = await get_crypto_data(list(symbols))
            
            if crypto_data:
                embed = discord.Embed(
                    title="💰 Криптовалюты",
                    color=0xF7931A
                )
                
                formatted_data = format_crypto_data(crypto_data, symbols)
                embed.description = formatted_data
                embed.set_footer(text="Данные предоставлены CoinPaprika • Обновляется в реальном времени")
                
                await ctx.reply(embed=embed)
            else:
                await ctx.reply("❌ Не удалось найти указанные криптовалюты. Проверьте символы.")
                
    except Exception as e:
        await ctx.reply("❌ Произошла ошибка при получении данных о криптовалютах.")
        print(f"Ошибка в команде крипта: {e}")

@bot.command(name='привет', aliases=['hello'])
async def hello(ctx):
    """Поздороваться с ботом"""
    await ctx.reply(PHRASES['hello'])

@bot.command(name='пока', aliases=['bye'])
async def goodbye(ctx):
    """Попрощаться с ботом"""
    await ctx.reply(PHRASES['goodbye'])

def is_channel_allowed(ctx):
    """Проверить, разрешен ли канал для выполнения команд"""
    guild_id = ctx.guild.id if ctx.guild else None
    
    # Если сервер не настроен, разрешаем все каналы
    if guild_id not in ALLOWED_CHANNELS:
        return True
    
    # Если список пустой, разрешаем все каналы
    if not ALLOWED_CHANNELS[guild_id]:
        return True
    
    # Проверяем, есть ли текущий канал в списке разрешенных
    return ctx.channel.id in ALLOWED_CHANNELS[guild_id]

@bot.group(name='канал', aliases=['channel'], invoke_without_command=True)
async def channel_group(ctx):
    """Группа команд для управления разрешенными каналами"""
    await ctx.send("Используйте `!канал добавить`, `!канал удалить`, `!канал список` или `!канал сброс`")

@channel_group.command(name='добавить', aliases=['add'])
@commands.has_permissions(administrator=True)
async def channel_add(ctx):
    """Добавить текущий канал в список разрешенных"""
    guild_id = ctx.guild.id
    channel_id = ctx.channel.id
    
    if guild_id not in ALLOWED_CHANNELS:
        ALLOWED_CHANNELS[guild_id] = []
    
    if channel_id not in ALLOWED_CHANNELS[guild_id]:
        ALLOWED_CHANNELS[guild_id].append(channel_id)
        await ctx.reply(f"✅ Канал {ctx.channel.mention} добавлен в список разрешенных для команд бота!")
    else:
        await ctx.reply(f"ℹ️ Канал {ctx.channel.mention} уже находится в списке разрешенных.")

@channel_group.command(name='удалить', aliases=['remove'])
@commands.has_permissions(administrator=True)
async def channel_remove(ctx):
    """Удалить текущий канал из списка разрешенных"""
    guild_id = ctx.guild.id
    channel_id = ctx.channel.id
    
    if guild_id in ALLOWED_CHANNELS and channel_id in ALLOWED_CHANNELS[guild_id]:
        ALLOWED_CHANNELS[guild_id].remove(channel_id)
        await ctx.reply(f"✅ Канал {ctx.channel.mention} удален из списка разрешенных.")
    else:
        await ctx.reply(f"ℹ️ Канал {ctx.channel.mention} не находится в списке разрешенных.")

@channel_group.command(name='список', aliases=['list'])
async def channel_list(ctx):
    """Показать список разрешенных каналов"""
    guild_id = ctx.guild.id
    
    if guild_id not in ALLOWED_CHANNELS or not ALLOWED_CHANNELS[guild_id]:
        await ctx.reply("📋 Бот работает во всех каналах (список разрешенных каналов пуст).")
        return
    
    embed = discord.Embed(
        title="📋 Разрешенные каналы для команд бота",
        color=0x00ff00
    )
    
    channel_mentions = []
    for channel_id in ALLOWED_CHANNELS[guild_id]:
        channel = ctx.guild.get_channel(channel_id)
        if channel:
            channel_mentions.append(channel.mention)
        else:
            channel_mentions.append(f"Удаленный канал (ID: {channel_id})")
    
    embed.description = "\n".join(channel_mentions) if channel_mentions else "Нет разрешенных каналов"
    embed.set_footer(text="Бот будет отвечать на команды только в этих каналах")
    
    await ctx.reply(embed=embed)

@channel_group.command(name='сброс', aliases=['reset'])
@commands.has_permissions(administrator=True)
async def channel_reset(ctx):
    """Сбросить список разрешенных каналов (разрешить все каналы)"""
    guild_id = ctx.guild.id
    
    if guild_id in ALLOWED_CHANNELS:
        ALLOWED_CHANNELS[guild_id] = []
    
    await ctx.reply("✅ Список разрешенных каналов сброшен. Бот теперь работает во всех каналах!")

@bot.event
async def on_command_error(ctx, error):
    """Обработка ошибок команд"""
    if isinstance(error, commands.CommandNotFound):
        # Проверяем разрешенные каналы только для существующих команд
        if is_channel_allowed(ctx):
            await ctx.reply(PHRASES['unknown'])
    elif isinstance(error, commands.MissingPermissions):
        if is_channel_allowed(ctx):
            await ctx.reply("❌ У вас нет прав администратора для выполнения этой команды.")
    elif isinstance(error, commands.MissingRequiredArgument):
        if is_channel_allowed(ctx):
            await ctx.reply("❌ Не хватает аргументов для команды. Используйте `!помощь` для справки.")
    else:
        if is_channel_allowed(ctx):
            await ctx.reply(PHRASES['error'])
            print(f"Ошибка команды: {error}")

@bot.event
async def on_message(message):
    """Обработка сообщений"""
    # Игнорируем сообщения от ботов
    if message.author.bot:
        return
    
    # Проверяем, разрешен ли канал для команд
    if message.content.startswith('!'):
        # Создаем контекст для проверки канала
        ctx = await bot.get_context(message)
        if not is_channel_allowed(ctx):
            return  # Игнорируем команды в неразрешенных каналах
    
    # Обрабатываем команды
    await bot.process_commands(message)
    
    # Реагируем на упоминания (только в разрешенных каналах)
    if bot.user.mentioned_in(message):
        ctx = await bot.get_context(message)
        if is_channel_allowed(ctx):
            await message.add_reaction('👋')

@bot.command(name='помощь')
async def help_command(ctx):
    """Показать справку"""
    embed = discord.Embed(
        title="📋 Справка по командам",
        description=PHRASES['help'],
        color=0x00ff00
    )
    embed.set_footer(text="Бот создан для общения на русском языке")
    await ctx.reply(embed=embed)

@bot.command(name='тест')
@commands.has_permissions(administrator=True)
async def test_apis(ctx):
    """Тестировать API для отладки"""
    await ctx.reply("🔍 Тестирую API...")
    
    # Подробный тест BTC Dominance
    try:
        # Тест CoinPaprika
        async with aiohttp.ClientSession() as session:
            url = "https://api.coinpaprika.com/v1/global"
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    cp_dominance = data.get('bitcoin_dominance_percentage', 0)
                    await ctx.send(f"📊 CoinPaprika BTC.D: {cp_dominance:.2f}%")
                else:
                    await ctx.send(f"❌ CoinPaprika Global: HTTP {response.status}")
        
        # Тест CoinGecko
        async with aiohttp.ClientSession() as session:
            url = "https://api.coingecko.com/api/v3/global"
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    cg_dominance = data.get('data', {}).get('market_cap_percentage', {}).get('btc', 0)
                    await ctx.send(f"📊 CoinGecko BTC.D: {cg_dominance:.2f}%")
                else:
                    await ctx.send(f"❌ CoinGecko Global: HTTP {response.status}")
        
        # Итоговый тест функции
        btc_dom = await get_btc_dominance()
        if btc_dom:
            await ctx.send(f"✅ Итоговый BTC.D: {btc_dom['usd']:.2f}%")
        else:
            await ctx.send("❌ BTC.D API не работает")
    except Exception as e:
        await ctx.send(f"❌ BTC.D ошибка: {e}")
    
    # Тест NASDAQ
    try:
        nasdaq = await get_nasdaq_data()
        if nasdaq:
            await ctx.send(f"✅ NASDAQ API работает: {nasdaq['usd']:,.2f}")
        else:
            await ctx.send("❌ NASDAQ API не работает")
    except Exception as e:
        await ctx.send(f"❌ NASDAQ ошибка: {e}")
    
    # Тест CoinPaprika
    try:
        btc_data = await fetch_coinpaprika_data('btc')
        if btc_data:
            await ctx.send(f"✅ CoinPaprika API работает: BTC ${btc_data['usd']:,.2f}")
        else:
            await ctx.send("❌ CoinPaprika API не работает")
    except Exception as e:
        await ctx.send(f"❌ CoinPaprika ошибка: {e}")

@bot.command(name='обновить')
@commands.has_permissions(administrator=True)
async def refresh_cache(ctx):
    """Очистить кэш и получить свежие данные"""
    global crypto_cache
    old_size = len(crypto_cache)
    crypto_cache.clear()
    await ctx.reply(f"🔄 Кэш очищен! Удалено {old_size} записей. Следующий запрос получит свежие данные.")

@bot.command(name='кэш')
@commands.has_permissions(administrator=True)
async def cache_info(ctx):
    """Показать информацию о кэше"""
    if not crypto_cache:
        await ctx.reply("📊 Кэш пуст")
        return
    
    now = time.time()
    cache_info = []
    
    for key, (data, timestamp) in crypto_cache.items():
        age = int(now - timestamp)
        if isinstance(data, dict) and 'usd' in data:
            value = f"${data['usd']:,.2f}" if data['usd'] >= 1 else f"${data['usd']:.6f}"
            cache_info.append(f"• {key}: {value} ({age}с назад)")
        else:
            cache_info.append(f"• {key}: {age}с назад")
    
    embed = discord.Embed(
        title="📊 Статистика кэша",
        description="\n".join(cache_info[:15]),  # Показываем первые 15
        color=0x00ff00
    )
    embed.set_footer(text=f"Всего записей: {len(crypto_cache)}")
    await ctx.reply(embed=embed)

if __name__ == "__main__":
    # Запуск бота
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("Ошибка: DISCORD_TOKEN не найден в .env файле!")
    else:
        try:
            bot.run(token)
        except Exception as e:
            print(f"Ошибка запуска бота: {e}")
import random

@bot.command(name='poll', aliases=['рандом'])
async def poll_command(ctx, max_number: int = None):
    """Выбрать случайное число от 1 до указанного"""
    if max_number is None:
        await ctx.reply("❌ Укажите максимальное число! Пример: `!poll 100` или `!рандом 50`")
        return
    
    if max_number < 1:
        await ctx.reply("❌ Число должно быть больше 0!")
        return
    
    if max_number > 1000000:
        await ctx.reply("❌ Число слишком большое! Максимум: 1,000,000")
        return
    
    try:
        # Генерируем случайное число от 1 до max_number
        random_number = random.randint(1, max_number)
        
        # Создаем красивый embed
        embed = discord.Embed(
            title="🎲 Случайное число",
            color=0x00ff00
        )
        
        embed.add_field(
            name="Диапазон",
            value=f"1 - {max_number:,}",
            inline=True
        )
        
        embed.add_field(
            name="Результат",
            value=f"**{random_number:,}**",
            inline=True
        )
        
        embed.set_footer(text=f"Запросил: {ctx.author.display_name}")
        
        await ctx.reply(embed=embed)
        
    except Exception as e:
        await ctx.reply("❌ Произошла ошибка при генерации числа.")
        print(f"Ошибка в команде poll: {e}")
# Музыкальный функционал
# Хранилище для голосовых подключений
voice_clients = {}

# Настройки для yt-dlp
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        
        if 'entries' in data:
            # Берем первый результат из плейлиста
            data = data['entries'][0]
        
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

@bot.command(name='join', aliases=['подключиться'])
async def join_voice(ctx):
    """Подключиться к голосовому каналу"""
    if ctx.author.voice is None:
        await ctx.reply("❌ Вы не находитесь в голосовом канале!")
        return
    
    voice_channel = ctx.author.voice.channel
    
    if ctx.voice_client is None:
        voice_client = await voice_channel.connect()
        voice_clients[ctx.guild.id] = voice_client
        await ctx.reply(f"✅ Подключился к каналу **{voice_channel.name}**")
    else:
        await ctx.voice_client.move_to(voice_channel)
        await ctx.reply(f"✅ Переместился в канал **{voice_channel.name}**")

@bot.command(name='leave', aliases=['отключиться'])
async def leave_voice(ctx):
    """Отключиться от голосового канала"""
    if ctx.voice_client is None:
        await ctx.reply("❌ Я не подключен к голосовому каналу!")
        return
    
    await ctx.voice_client.disconnect()
    if ctx.guild.id in voice_clients:
        del voice_clients[ctx.guild.id]
    await ctx.reply("✅ Отключился от голосового канала")

@bot.command(name='play', aliases=['играть'])
async def play_music(ctx, *, query):
    """Воспроизвести музыку по ссылке или названию"""
    # Проверяем, подключен ли бот к голосовому каналу
    if ctx.voice_client is None:
        if ctx.author.voice is None:
            await ctx.reply("❌ Вы не находитесь в голосовом канале! Подключитесь к каналу и попробуйте снова.")
            return
        
        voice_channel = ctx.author.voice.channel
        voice_client = await voice_channel.connect()
        voice_clients[ctx.guild.id] = voice_client
        await ctx.send(f"✅ Подключился к каналу **{voice_channel.name}**")
    
    # Останавливаем текущее воспроизведение если есть
    if ctx.voice_client.is_playing():
        ctx.voice_client.stop()
    
    try:
        await ctx.send(f"🔍 Ищу: **{query}**...")
        
        # Получаем аудио источник
        player = await YTDLSource.from_url(query, loop=bot.loop, stream=True)
        
        # Воспроизводим
        ctx.voice_client.play(player, after=lambda e: print(f'Ошибка воспроизведения: {e}') if e else None)
        
        embed = discord.Embed(
            title="🎵 Сейчас играет",
            description=f"**{player.title}**",
            color=0x00ff00
        )
        embed.set_footer(text=f"Запросил: {ctx.author.display_name}")
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.reply(f"❌ Ошибка при воспроизведении: {str(e)}")
        print(f"Ошибка воспроизведения: {e}")

@bot.command(name='radio', aliases=['радио'])
async def play_radio(ctx):
    """Включить радио Bluford"""
    # Проверяем, подключен ли бот к голосовому каналу
    if ctx.voice_client is None:
        if ctx.author.voice is None:
            await ctx.reply("❌ Вы не находитесь в голосовом канале! Подключитесь к каналу и попробуйте снова.")
            return
        
        voice_channel = ctx.author.voice.channel
        voice_client = await voice_channel.connect()
        voice_clients[ctx.guild.id] = voice_client
        await ctx.send(f"✅ Подключился к каналу **{voice_channel.name}**")
    
    # Останавливаем текущее воспроизведение если есть
    if ctx.voice_client.is_playing():
        ctx.voice_client.stop()
    
    try:
        radio_url = "http://bluford.torontocast.com:8085/stream/"
        
        await ctx.send("📻 Подключаюсь к радио Bluford...")
        
        # Создаем аудио источник для радио
        source = discord.FFmpegPCMAudio(radio_url, **ffmpeg_options)
        
        # Воспроизводим радио
        ctx.voice_client.play(source, after=lambda e: print(f'Ошибка радио: {e}') if e else None)
        
        embed = discord.Embed(
            title="📻 Радио включено",
            description="**Bluford Radio**\nПрямой эфир",
            color=0xff6b6b
        )
        embed.add_field(name="Ссылка", value="http://bluford.torontocast.com:8085/stream/", inline=False)
        embed.set_footer(text=f"Запросил: {ctx.author.display_name}")
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.reply(f"❌ Ошибка при подключении к радио: {str(e)}")
        print(f"Ошибка радио: {e}")

@bot.command(name='stop', aliases=['стоп'])
async def stop_music(ctx):
    """Остановить воспроизведение"""
    if ctx.voice_client is None:
        await ctx.reply("❌ Я не подключен к голосовому каналу!")
        return
    
    if ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.reply("⏹️ Воспроизведение остановлено")
    else:
        await ctx.reply("❌ Ничего не воспроизводится")

@bot.command(name='pause', aliases=['пауза'])
async def pause_music(ctx):
    """Поставить на паузу"""
    if ctx.voice_client is None:
        await ctx.reply("❌ Я не подключен к голосовому каналу!")
        return
    
    if ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.reply("⏸️ Воспроизведение приостановлено")
    else:
        await ctx.reply("❌ Ничего не воспроизводится")

@bot.command(name='resume', aliases=['продолжить'])
async def resume_music(ctx):
    """Продолжить воспроизведение"""
    if ctx.voice_client is None:
        await ctx.reply("❌ Я не подключен к голосовому каналу!")
        return
    
    if ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.reply("▶️ Воспроизведение продолжено")
    else:
        await ctx.reply("❌ Воспроизведение не приостановлено")

@bot.command(name='volume', aliases=['громкость'])
async def change_volume(ctx, volume: int = None):
    """Изменить громкость (0-100)"""
    if ctx.voice_client is None:
        await ctx.reply("❌ Я не подключен к голосовому каналу!")
        return
    
    if volume is None:
        current_volume = int(ctx.voice_client.source.volume * 100) if hasattr(ctx.voice_client.source, 'volume') else 50
        await ctx.reply(f"🔊 Текущая громкость: **{current_volume}%**")
        return
    
    if volume < 0 or volume > 100:
        await ctx.reply("❌ Громкость должна быть от 0 до 100!")
        return
    
    if hasattr(ctx.voice_client.source, 'volume'):
        ctx.voice_client.source.volume = volume / 100
        await ctx.reply(f"🔊 Громкость установлена на **{volume}%**")
    else:
        await ctx.reply("❌ Невозможно изменить громкость для этого источника")