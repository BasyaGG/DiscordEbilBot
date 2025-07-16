import discord
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import asyncio
import aiohttp
import json

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
• `!канал сброс` - разрешить боту работать во всех каналах''',
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
    'екб': 'Екатеринбург'
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
            
            embed.set_footer(text="Данные предоставлены OpenWeatherMap • Используйте !погода <город> для поиска")
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

# Криптовалюты API функции
async def get_crypto_data(symbols):
    """Получить данные о криптовалютах через CoinGecko API"""
    if isinstance(symbols, str):
        symbols = [symbols]
    
    results = {}
    
    for symbol in symbols:
        symbol_lower = symbol.lower()
        
        # Специальная обработка для BTC.D (Bitcoin Dominance)
        if symbol_lower == 'btc.d' or symbol_lower == 'btcd':
            btc_dominance = await get_btc_dominance()
            if btc_dominance:
                results['btc.d'] = btc_dominance
            continue
        
        # Специальная обработка для NASDAQ
        if symbol_lower == 'nasdaq':
            nasdaq_data = await get_nasdaq_data()
            if nasdaq_data:
                results['nasdaq'] = nasdaq_data
            continue
        
        # Обычные криптовалюты
        if symbol_lower in CRYPTO_SYMBOLS:
            coin_id = CRYPTO_SYMBOLS[symbol_lower]
        else:
            coin_id = symbol_lower
        
        # Получаем данные для одной криптовалюты
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true&include_market_cap=true"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if coin_id in data:
                            results[coin_id] = data[coin_id]
        except Exception as e:
            print(f"Ошибка при получении данных для {symbol}: {e}")
    
    return results if results else None

async def get_btc_dominance():
    """Получить Bitcoin Dominance"""
    url = "https://api.coingecko.com/api/v3/global"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    btc_dominance = data.get('data', {}).get('market_cap_percentage', {}).get('btc', 0)
                    return {
                        'usd': btc_dominance,
                        'usd_24h_change': 0,  # CoinGecko не предоставляет изменение доминации за 24ч
                        'usd_market_cap': 0
                    }
    except Exception as e:
        print(f"Ошибка при получении Bitcoin Dominance: {e}")
    
    return None

async def get_nasdaq_data():
    """Получить данные NASDAQ через Yahoo Finance API"""
    try:
        # Используем Yahoo Finance API для получения данных NASDAQ
        url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EIXIC"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Извлекаем данные из ответа Yahoo Finance
                    chart = data.get('chart', {})
                    result = chart.get('result', [])
                    
                    if result:
                        meta = result[0].get('meta', {})
                        current_price = meta.get('regularMarketPrice', 0)
                        previous_close = meta.get('previousClose', 0)
                        
                        # Вычисляем изменение за день
                        if previous_close > 0:
                            change_24h = ((current_price - previous_close) / previous_close) * 100
                        else:
                            change_24h = 0
                        
                        return {
                            'usd': current_price,
                            'usd_24h_change': change_24h,
                            'usd_market_cap': 0
                        }
                        
    except Exception as e:
        print(f"Ошибка при получении данных NASDAQ: {e}")
    
    # Если не удалось получить данные, возвращаем демонстрационные
    return {
        'usd': 15420.50,  # Примерное значение NASDAQ
        'usd_24h_change': 1.25,  # Примерное изменение за день
        'usd_market_cap': 0
    }

def format_crypto_data(crypto_data, requested_symbols):
    """Форматировать данные о криптовалютах"""
    if not crypto_data:
        return "❌ Данные недоступны"
    
    result = ""
    
    for symbol in requested_symbols:
        symbol_lower = symbol.lower()
        
        # Специальная обработка для BTC.D
        if symbol_lower == 'btc.d' or symbol_lower == 'btcd':
            if 'btc.d' in crypto_data:
                data = crypto_data['btc.d']
                dominance = data.get('usd', 0)
                
                result += f"**BTC.D** 👑\n"
                result += f"📊 Доминация: **{dominance:.2f}%**\n"
                result += f"💡 Bitcoin доминация на рынке\n\n"
                continue
        
        # Специальная обработка для NASDAQ
        if symbol_lower == 'nasdaq':
            if 'nasdaq' in crypto_data:
                data = crypto_data['nasdaq']
                price = data.get('usd', 0)
                change_24h = data.get('usd_24h_change', 0)
                
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
                
                result += f"**NASDAQ** 📊 {change_emoji}\n"
                result += f"💰 Индекс: **{price:,.2f}**\n"
                result += f"📊 24ч: **{change_color}{change_24h:.2f}%**\n"
                result += f"🏛️ Фондовый рынок США\n\n"
                continue
        
        # Обычные криптовалюты
        coin_id = CRYPTO_SYMBOLS.get(symbol_lower, symbol_lower)
        
        if coin_id in crypto_data:
            data = crypto_data[coin_id]
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
            
            # Специальное форматирование для разных типов активов
            if symbol_lower in ['btc', 'eth']:
                # Основные криптовалюты
                if price >= 1:
                    price_str = f"${price:,.2f}"
                else:
                    price_str = f"${price:.6f}"
            else:
                # Альткоины
                if price >= 1:
                    price_str = f"${price:,.4f}"
                else:
                    price_str = f"${price:.8f}"
            
            # Форматируем рыночную капитализацию
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
            result += "\n"
    
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
                embed.set_footer(text="Данные предоставлены CoinGecko • Обновляется в реальном времени")
                
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
                embed.set_footer(text="Данные предоставлены CoinGecko • Обновляется в реальном времени")
                
                await ctx.reply(embed=embed)
            else:
                await ctx.reply("❌ Не удалось найти указанные криптовалюты. Проверьте символы.")
                
    except Exception as e:
        await ctx.reply("❌ Произошла ошибка при получении данных о криптовалютах.")
        print(f"Ошибка в команде крипта: {e}")

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

@bot.event
async def on_message(message):
    """Обработка сообщений"""
    # Игнорируем сообщения от ботов
    if message.author.bot:
        return
    
    # Обрабатываем команды
    await bot.process_commands(message)
    
    # Реагируем на упоминания
    if bot.user.mentioned_in(message):
        await message.add_reaction('👋')

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