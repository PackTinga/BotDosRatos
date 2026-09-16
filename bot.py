import discord
from discord.ext import commands
import random
import json
import os
import time
import threading
from flask import Flask

# =========================================================
# CONFIGURAÇÃO
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)

# =========================================================
# ARQUIVOS
# =========================================================

PONTOS_FILE = "pontos.json"
PERFIL_FILE = "perfil.json"
QUIZ_USADAS_FILE = "quiz_usadas.json"
INVENTARIO_FILE = "inventario.json"
IMG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "imagens")
AUDIO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audios")

COOLDOWN_PONTOS = 100

cooldowns = {}
jogos = {}
quiz_ativos = {}
interacao_cooldown = {}

# 🎰 Cooldown individual do slot
slot_cooldowns = {}
COOLDOWN_SLOT = 120

# 👑 Sistema do Rei do Server
REI_ID = 1169781481376338000
elogio_cooldown = {}
COOLDOWN_ELOGIO = 5

ELOGIOS_REI = [
    "👑 O Rei do Server falou!",
    "🐀 Respeita o maior rato da história.",
    "🏆 Sua majestade se pronunciou.",
    "🔥 O homem está on.",
    "👑 Silêncio na rataria, o Rei está falando.",
    "🐀 O verdadeiro dono desse servidor apareceu.",
    "👑 Atenção! O Rei do Server está falando.",
    "🔥 Lá vem ele, o homem mais importante da rataria.",
    "🏆 Respeita a lenda.",
    "👑 Sua majestade mandou mensagem."
]

# =========================================================
# JSON
# =========================================================

def carregar_json(arquivo, padrao):
    if not os.path.exists(arquivo):
        return padrao

    try:
        with open(arquivo, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return padrao


def salvar_json(arquivo, dados):
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)


# =========================================================
# DADOS
# =========================================================

# IMPORTANTE:
# O dicionário se chama pontos_data.
# Isso evita o conflito com o comando !pontos.

pontos_data = carregar_json(PONTOS_FILE, {})
perfis = carregar_json(PERFIL_FILE, {})
quiz_usadas = carregar_json(QUIZ_USADAS_FILE, {})
inventarios = carregar_json(INVENTARIO_FILE, {})


# =========================================================
# SISTEMA DE PONTOS
# =========================================================

def setup_user(user_id):
    user_id = str(user_id)

    if user_id not in pontos_data:
        pontos_data[user_id] = 0
        salvar_json(PONTOS_FILE, pontos_data)

    if user_id not in perfis:
        perfis[user_id] = {
            "xp": 0,
            "jogos": 0,
            "vitorias": 0,
            "derrotas": 0,
            "empates": 0
        }
        salvar_json(PERFIL_FILE, perfis)

    if user_id not in inventarios:
        inventarios[user_id] = {}
        salvar_json(INVENTARIO_FILE, inventarios)


def get_pontos(user_id):
    setup_user(user_id)
    return pontos_data[str(user_id)]


def add_points(user_id, quantidade):
    setup_user(user_id)

    user_id = str(user_id)
    pontos_data[user_id] += quantidade

    salvar_json(PONTOS_FILE, pontos_data)


def add_xp(user_id, quantidade):
    setup_user(user_id)

    user_id = str(user_id)
    perfis[user_id]["xp"] += quantidade

    salvar_json(PERFIL_FILE, perfis)


def game_result(user_id, resultado):
    setup_user(user_id)

    user_id = str(user_id)

    perfis[user_id]["jogos"] += 1

    if resultado == "win":
        perfis[user_id]["vitorias"] += 1

    elif resultado == "loss":
        perfis[user_id]["derrotas"] += 1

    elif resultado == "draw":
        perfis[user_id]["empates"] += 1

    salvar_json(PERFIL_FILE, perfis)


def nivel_usuario(user_id):
    setup_user(user_id)

    xp = perfis[str(user_id)]["xp"]

    return (xp // 100) + 1


# =========================================================
# 🛒 LOJA DOS RATOS
# =========================================================

LOJA = {
    # STATUS
    "1": {"nome": "🐀 Rato", "preco": 500, "tipo": "cargo", "cargo": "🐀 Rato", "beneficio": "Cargo Rato exclusivo."},
    "2": {"nome": "😎 Rato Brabo", "preco": 1000, "tipo": "cargo", "cargo": "😎 Rato Brabo", "beneficio": "Cargo Rato Brabo."},
    "3": {"nome": "👑 Rato VIP", "preco": 2000, "tipo": "cargo", "cargo": "👑 Rato VIP", "beneficio": "Cargo VIP + 2 pontos por mensagem."},
    "4": {"nome": "💎 Rato Premium", "preco": 3500, "tipo": "cargo", "cargo": "💎 Rato Premium", "beneficio": "Cargo Premium."},
    "5": {"nome": "🏆 Rato Lendário", "preco": 5000, "tipo": "cargo", "cargo": "🏆 Rato Lendário", "beneficio": "Cargo Lendário + 3 pontos por mensagem."},
    "6": {"nome": "🌟 Rato Supremo", "preco": 10000, "tipo": "cargo", "cargo": "🌟 Rato Supremo", "beneficio": "Cargo Supremo."},
    "7": {"nome": "🐀 Deus da Rataria", "preco": 25000, "tipo": "cargo", "cargo": "🐀 Deus da Rataria", "beneficio": "Cargo Deus da Rataria."},

    # COSMÉTICOS
    "8": {"nome": "🎨 Cor Exclusiva", "preco": 8000, "tipo": "cargo", "cargo": "🎨 Cor Exclusiva", "beneficio": "Cargo com cor exclusiva."},
    "9": {"nome": "🌈 Cor Arco-Íris", "preco": 12000, "tipo": "cargo", "cargo": "🌈 Cor Arco-Íris", "beneficio": "Cargo Arco-Íris."},
    "10": {"nome": "✨ Nome Brilhante", "preco": 15000, "tipo": "cargo", "cargo": "✨ Nome Brilhante", "beneficio": "Cargo Nome Brilhante."},
    "11": {"nome": "🔥 Nome Flamejante", "preco": 20000, "tipo": "cargo", "cargo": "🔥 Nome Flamejante", "beneficio": "Cargo Nome Flamejante."},
    "12": {"nome": "💎 Cargo Diamante", "preco": 30000, "tipo": "cargo", "cargo": "💎 Cargo Diamante", "beneficio": "Cargo Diamante."},

    # JOGOS
    "13": {"nome": "🍀 Ticket da Sorte", "preco": 300, "tipo": "item", "beneficio": "Ticket da Sorte para usar no sistema de jogos."},
    "14": {"nome": "🎰 Ficha Especial", "preco": 1000, "tipo": "item", "beneficio": "Ficha Especial para usar no sistema de jogos."},
    "15": {"nome": "🎲 Dado da Fortuna", "preco": 1500, "tipo": "item", "beneficio": "Dado da Fortuna para usar no sistema de jogos."},
    "16": {"nome": "⚔️ Ticket de Briga", "preco": 1500, "tipo": "item", "beneficio": "Ticket de Briga para usar no sistema de briga."},
    "17": {"nome": "🃏 Carta Coringa", "preco": 2000, "tipo": "item", "beneficio": "Carta Coringa para usar em jogos."},
    "18": {"nome": "💰 Multiplicador", "preco": 3000, "tipo": "item", "beneficio": "Multiplicador para usar no sistema de jogos."},

    # MEMES
    "19": {"nome": "🐀 Rato de Estimação", "preco": 1000, "tipo": "cargo", "cargo": "🐀 Rato de Estimação", "beneficio": "Cargo Rato de Estimação."},
    "20": {"nome": "🗿 Estátua do Rato", "preco": 2500, "tipo": "cargo", "cargo": "🗿 Estátua do Rato", "beneficio": "Cargo Estátua do Rato."},
    "21": {"nome": "🤡 Cargo Palhaço", "preco": 4000, "tipo": "cargo", "cargo": "🤡 Cargo Palhaço", "beneficio": "Cargo Palhaço."},
    "22": {"nome": "💀 Cargo Quase Morto", "preco": 3000, "tipo": "cargo", "cargo": "💀 Cargo Quase Morto", "beneficio": "Cargo Quase Morto."},
    "23": {"nome": "🗿 Cargo Monolito", "preco": 5000, "tipo": "cargo", "cargo": "🗿 Cargo Monolito", "beneficio": "Cargo Monolito."},
    "24": {"nome": "🚨 Cargo Procurado", "preco": 7500, "tipo": "cargo", "cargo": "🚨 Cargo Procurado", "beneficio": "Cargo Procurado."},
    "25": {"nome": "🧠 Cargo Gênio", "preco": 10000, "tipo": "cargo", "cargo": "🧠 Cargo Gênio", "beneficio": "Cargo Gênio."},

    # ESPECIAIS
    "26": {"nome": "🍀 Ticket Supremo", "preco": 5000, "tipo": "item", "beneficio": "Ticket Supremo para usar no sistema de jogos."},
    "27": {"nome": "☠️ Imunidade", "preco": 5000, "tipo": "item", "beneficio": "Imunidade para uso em mecânicas compatíveis."},
    "28": {"nome": "👑 Título Personalizado", "preco": 15000, "tipo": "item", "beneficio": "Título personalizado."},
    "29": {"nome": "💎 Cargo Exclusivo", "preco": 25000, "tipo": "cargo", "cargo": "💎 Cargo Exclusivo", "beneficio": "Cargo Exclusivo."},
    "30": {"nome": "🏰 Cargo Supremo", "preco": 40000, "tipo": "cargo", "cargo": "🏰 Cargo Supremo", "beneficio": "Cargo Supremo."},
    "31": {"nome": "🌌 Cargo Lendário", "preco": 50000, "tipo": "cargo", "cargo": "🌌 Cargo Lendário", "beneficio": "Cargo Lendário."},
    "32": {"nome": "🐀👑 DEUS DA RATARIA", "preco": 100000, "tipo": "cargo", "cargo": "🐀👑 DEUS DA RATARIA", "beneficio": "Cargo máximo da Rataria."}
}


def multiplicador_pontos(user_id):
    # O cargo Lendário tem prioridade sobre o VIP.
    for guild in bot.guilds:
        membro = guild.get_member(int(user_id))
        if membro is None:
            continue

        if discord.utils.get(membro.roles, name="🏆 Rato Lendário"):
            return 3

        if discord.utils.get(membro.roles, name="👑 Rato VIP"):
            return 2

    return 1


# =========================================================
# BOT ONLINE
# =========================================================

@bot.event
async def on_ready():
    print(f"🤖 {bot.user} está online!")
    print("🧠 Sistema de jogos carregado.")
    print("💬 Interações automáticas ativadas.")


# =========================================================
# PONTOS POR MENSAGEM
# =========================================================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    user_id = message.author.id
    agora = time.time()

    setup_user(user_id)

    # 👑 ELOGIO AO REI DO SERVER
    texto = message.content.lower().strip()

    if (
        message.author.id == REI_ID
        and not texto.startswith("!")
    ):
        agora_elogio = time.time()
        ultimo_elogio = elogio_cooldown.get(message.author.id, 0)

        if agora_elogio - ultimo_elogio >= COOLDOWN_ELOGIO:
            elogio_cooldown[message.author.id] = agora_elogio

            await message.channel.send(
                random.choice(ELOGIOS_REI)
            )

    # 💰 Pontos por mensagem
    if (
        user_id not in cooldowns
        or agora - cooldowns[user_id] >= COOLDOWN_PONTOS
    ):
        ganho = multiplicador_pontos(user_id)
        add_points(user_id, ganho)
        cooldowns[user_id] = agora

    # =====================================================
    # 🖼️ IMAGENS + 🔊 ÁUDIOS AUTOMÁTICOS
    # =====================================================

    imagens = {
        "bolsonaro": "bolsonaro.png",
        "lula": "lula.png",
        "lula e bolsonaro": "lula-e-bolsonaro.png",
        "bolsonaro e lula": "lula-e-bolsonaro.png",
        "!bot farmar aura": "farmar-aura.png"
    }

    audios = {
        "bolsonaro": "bolsonaro.mp3",
        "lula": "lula.mp3",
        "!bot farmar aura": "farmar_aura.mp3"
    }

    # Envia a imagem quando houver uma palavra cadastrada
    if texto in imagens:
        caminho_imagem = os.path.join(IMG_DIR, imagens[texto])

        if os.path.exists(caminho_imagem):
            await message.channel.send(
                file=discord.File(caminho_imagem)
            )

    # Toca o áudio somente para Bolsonaro/Lula
    if texto in audios:
        caminho_audio = os.path.join(AUDIO_DIR, audios[texto])

        if os.path.exists(caminho_audio):
            if message.author.voice and message.author.voice.channel:
                canal = message.author.voice.channel

                try:
                    voice = message.guild.voice_client

                    if voice is None:
                        voice = await canal.connect()
                    elif voice.channel != canal:
                        await voice.move_to(canal)

                    if voice.is_playing():
                        voice.stop()

                    source = discord.FFmpegPCMAudio(caminho_audio)
                    voice.play(source)

                    # Envia o mesmo MP3 no chat.
                    await message.channel.send(
                        file=discord.File(caminho_audio)
                    )

                except Exception as e:
                    print(f"[ÁUDIO] Erro ao tocar {texto}: {e}")
            else:
                print(
                    f"[ÁUDIO] {texto}: autor não está em canal de voz."
                )
                await message.channel.send(
                    file=discord.File(caminho_audio)
                )
        else:
            print(f"[ÁUDIO] Arquivo não encontrado: {caminho_audio}")

    # =====================================================
    # 💬 RESPOSTAS AUTOMÁTICAS
    # =====================================================

    respostas = {
        "oi": [
            "falaaa 😎",
            "opa KKKKK",
            "salve rato 🐀",
            "fala aí"
        ],
        "ola": [
            "olaaaa 👋",
            "opa!",
            "salve 😎"
        ],
        "bom dia": [
            "bom diaaa ☀️",
            "bom dia rato 🐀"
        ],
        "boa tarde": [
            "boa tarde 😎",
            "boa tardeee"
        ],
        "boa noite": [
            "boa noite 🌙",
            "boa noite rato 🐀"
        ],
        "kkkk": [
            "KKKKKKKKKKKK",
            "KKKKKKKKKKKKKKKK",
            "tá rindo do quê maluco KKKK"
        ],
        "kkk": [
            "KKKKKKKK",
            "ihhh tá rindo KKKK"
        ]
    }

    if texto in respostas:
        agora_interacao = time.time()
        chave = f"{message.channel.id}"

        if (
            chave not in interacao_cooldown
            or agora_interacao - interacao_cooldown[chave] >= 8
        ):
            interacao_cooldown[chave] = agora_interacao

            await message.channel.send(
                random.choice(respostas[texto])
            )

    # Processa os comandos !comando
    await bot.process_commands(message)

# =========================================================
# !PONTOS
# =========================================================

@bot.command(name="pontos")
async def pontos(ctx, pessoa: discord.Member = None):

    if pessoa is None:
        pessoa = ctx.author

    saldo = get_pontos(pessoa.id)

    embed = discord.Embed(
        title="🏆 Pontos",
        description=(
            f"**{pessoa.display_name}** possui "
            f"**{saldo} pontos**."
        )
    )

    await ctx.send(embed=embed)


# =========================================================
# !RANKING
# =========================================================

@bot.command()
async def ranking(ctx):

    if not pontos_data:
        await ctx.send(
            "🏆 Ainda não existem pontos no servidor!"
        )
        return

    ranking_data = sorted(
        pontos_data.items(),
        key=lambda x: x[1],
        reverse=True
    )

    texto = ""

    for posicao, (user_id, quantidade) in enumerate(
        ranking_data[:10],
        start=1
    ):

        membro = ctx.guild.get_member(int(user_id))

        if membro:
            texto += (
                f"**{posicao}.** "
                f"{membro.display_name} — "
                f"🏆 **{quantidade} pts**\n"
            )

    if not texto:
        texto = "Ainda não existem membros no ranking."

    embed = discord.Embed(
        title="🏆 RANKING DOS RATOS",
        description=texto
    )

    await ctx.send(embed=embed)


# =========================================================
# !PERFIL
# =========================================================

@bot.command()
async def perfil(ctx, pessoa: discord.Member = None):

    if pessoa is None:
        pessoa = ctx.author

    setup_user(pessoa.id)

    dados = perfis[str(pessoa.id)]

    xp = dados["xp"]
    nivel = nivel_usuario(pessoa.id)

    embed = discord.Embed(
        title=f"🐀 Perfil de {pessoa.display_name}"
    )

    embed.set_thumbnail(
        url=pessoa.display_avatar.url
    )

    embed.add_field(
        name="💰 Pontos",
        value=f"**{get_pontos(pessoa.id)}**",
        inline=True
    )

    embed.add_field(
        name="⭐ Nível",
        value=f"**{nivel}**",
        inline=True
    )

    embed.add_field(
        name="✨ XP",
        value=f"**{xp}**",
        inline=True
    )

    embed.add_field(
        name="🎮 Jogos",
        value=f"**{dados['jogos']}**",
        inline=True
    )

    embed.add_field(
        name="🏆 Vitórias",
        value=f"**{dados['vitorias']}**",
        inline=True
    )

    embed.add_field(
        name="💀 Derrotas",
        value=f"**{dados['derrotas']}**",
        inline=True
    )

    embed.add_field(
        name="🤝 Empates",
        value=f"**{dados['empates']}**",
        inline=True
    )

    await ctx.send(embed=embed)


# =========================================================
# !LOJA
# =========================================================

@bot.command()
async def loja(ctx):
    categorias = {
        "🐀 STATUS": range(1, 8),
        "🎨 COSMÉTICOS": range(8, 13),
        "🎰 JOGOS": range(13, 19),
        "😂 MEMES": range(19, 26),
        "👑 ESPECIAIS": range(26, 33)
    }

    await ctx.send(
        "🛒 **LOJA DA RATARIA**\n"
        "💰 Use `!comprar número` para comprar."
    )

    # Uma mensagem por categoria evita o limite de 2.000 caracteres do Discord.
    for categoria, numeros in categorias.items():
        linhas = [f"**{categoria}**", "━━━━━━━━━━━━━━━━"]

        for numero in numeros:
            item = LOJA[str(numero)]
            preco = f"{item['preco']:,}".replace(",", ".")
            linhas.append(
                f"**{numero}. {item['nome']}** — **{preco} pontos**\n"
                f"└ {item['beneficio']}\n"
                f"└ `!comprar {numero}`"
            )

        texto = "\n".join(linhas)
        # Segurança extra: quebra qualquer categoria inesperadamente grande.
        if len(texto) <= 1900:
            await ctx.send(texto)
        else:
            bloco = ""
            for linha in linhas:
                if len(bloco) + len(linha) + 1 > 1900:
                    await ctx.send(bloco)
                    bloco = linha
                else:
                    bloco += ("\n" if bloco else "") + linha
            if bloco:
                await ctx.send(bloco)

    await ctx.send("💰 Use `!pontos` para ver seu saldo.")


# =========================================================
# !COMPRAR
# =========================================================

@bot.command()
async def comprar(ctx, numero=None):
    if numero is None:
        await ctx.send("❌ Use `!loja` para ver os produtos e depois `!comprar número`.")
        return

    numero = str(numero).strip()

    if numero not in LOJA:
        await ctx.send("❌ Produto inválido! Use `!loja`.")
        return

    item = LOJA[numero]
    saldo = get_pontos(ctx.author.id)
    preco = item["preco"]

    if saldo < preco:
        faltam = preco - saldo
        await ctx.send(
            f"❌ **Pontos insuficientes!**\n\n"
            f"🛒 Produto: **{item['nome']}**\n"
            f"💰 Preço: **{preco:,} pontos**\n"
            f"💳 Seu saldo: **{saldo:,} pontos**\n"
            f"📉 Faltam: **{faltam:,} pontos**"
            .replace(",", ".")
        )
        return

    # Produtos do tipo cargo entregam um cargo real do Discord.
    if item["tipo"] == "cargo":
        cargo = discord.utils.get(ctx.guild.roles, name=item["cargo"])

        if cargo is None:
            await ctx.send(
                f"❌ O cargo **{item['cargo']}** não existe no servidor.\n"
                "Crie o cargo e deixe o cargo do bot acima dele."
            )
            return

        if cargo in ctx.author.roles:
            await ctx.send(f"❌ Você já possui **{cargo.name}**!")
            return

        try:
            await ctx.author.add_roles(cargo, reason=f"Compra da loja #{numero}")
        except discord.Forbidden:
            await ctx.send(
                "❌ Não consegui entregar o cargo. Verifique **Gerenciar Cargos** "
                "e se o cargo do bot está acima do cargo comprado."
            )
            return
        except discord.HTTPException as e:
            print(f"[LOJA] Erro ao entregar cargo: {e}")
            await ctx.send("❌ O Discord recusou a entrega do cargo. Tente novamente.")
            return

    # Produtos do tipo item ficam salvos no inventário.
    elif item["tipo"] == "item":
        user_id = str(ctx.author.id)
        inventarios.setdefault(user_id, {})
        inventarios[user_id][numero] = inventarios[user_id].get(numero, 0) + 1
        salvar_json(INVENTARIO_FILE, inventarios)

    else:
        await ctx.send("❌ Tipo de produto inválido na configuração da loja.")
        return

    add_points(ctx.author.id, -preco)

    await ctx.send(
        f"🎉 **COMPRA REALIZADA!**\n\n"
        f"👤 {ctx.author.mention}\n"
        f"🎁 {item['nome']}\n"
        f"💰 -{preco:,} pontos\n"
        f"✨ **Benefício:** {item['beneficio']}\n"
        f"💳 Saldo: **{get_pontos(ctx.author.id):,} pontos**"
        .replace(",", ".")
    )


# =========================================================
# !INVENTARIO
# =========================================================

@bot.command()
async def inventario(ctx):
    setup_user(ctx.author.id)
    itens = inventarios.get(str(ctx.author.id), {})

    if not itens:
        await ctx.send("🎒 Seu inventário está vazio.")
        return

    linhas = [f"🎒 **INVENTÁRIO DE {ctx.author.display_name}**", ""]

    for numero, quantidade in itens.items():
        item = LOJA.get(str(numero))
        if item is not None and quantidade > 0:
            linhas.append(f"{item['nome']} — **x{quantidade}**")

    if len(linhas) == 2:
        await ctx.send("🎒 Seu inventário está vazio.")
        return

    await ctx.send("\n".join(linhas))


# =========================================================
# ADMIN — !ADD PONTOS
# =========================================================

@bot.command()
@commands.has_permissions(administrator=True)
async def addpontos(
    ctx,
    pessoa: discord.Member,
    quantidade: int
):

    if quantidade <= 0:
        await ctx.send("❌ Quantidade inválida.")
        return

    add_points(
        pessoa.id,
        quantidade
    )

    await ctx.send(
        f"✅ Adicionados **{quantidade} pontos** "
        f"para **{pessoa.display_name}**.\n"
        f"💰 Saldo: **{get_pontos(pessoa.id)}**"
    )


# =========================================================
# ADMIN — !REMOVE PONTOS
# =========================================================

@bot.command()
@commands.has_permissions(administrator=True)
async def removepontos(
    ctx,
    pessoa: discord.Member,
    quantidade: int
):

    if quantidade <= 0:
        await ctx.send("❌ Quantidade inválida.")
        return

    saldo = get_pontos(pessoa.id)

    novo_saldo = max(
        0,
        saldo - quantidade
    )

    pontos_data[str(pessoa.id)] = novo_saldo

    salvar_json(
        PONTOS_FILE,
        pontos_data
    )

    await ctx.send(
        f"✅ Removidos **{quantidade} pontos** "
        f"de **{pessoa.display_name}**.\n"
        f"💰 Saldo: **{novo_saldo}**"
    )


# =========================================================
# ADMIN — !ZERARPONTOS
# =========================================================

@bot.command()
@commands.has_permissions(administrator=True)
async def zerarpontos(
    ctx,
    pessoa: discord.Member
):

    pontos_data[str(pessoa.id)] = 0

    salvar_json(
        PONTOS_FILE,
        pontos_data
    )

    await ctx.send(
        f"🗑️ Pontos de **{pessoa.display_name}** zerados!"
    )


# =========================================================
# 🎰 SLOT
# =========================================================

@bot.command()
async def slot(ctx):

    agora = time.time()
    ultimo_slot = slot_cooldowns.get(ctx.author.id, 0)
    restante = COOLDOWN_SLOT - (agora - ultimo_slot)

    if restante > 0:
        minutos = int(restante // 60)
        segundos = int(restante % 60)

        await ctx.send(
            f"⏳ {ctx.author.mention}, calma aí!\n"
            f"🎰 Você precisa esperar **{minutos}m {segundos}s** "
            f"para jogar novamente."
        )
        return

    custo = 20
    saldo = get_pontos(ctx.author.id)

    if saldo < custo:
        await ctx.send(
            f"❌ Você precisa de **{custo} pontos**.\n"
            f"💰 Saldo: **{saldo}**"
        )
        return

    slot_cooldowns[ctx.author.id] = agora

    add_points(
        ctx.author.id,
        -custo
    )

    simbolos = [
        "🍒",
        "🍋",
        "🍉",
        "⭐",
        "💎"
    ]

    resultado = [
        random.choice(simbolos),
        random.choice(simbolos),
        random.choice(simbolos)
    ]

    if resultado[0] == resultado[1] == resultado[2]:
        premio = 500
        add_points(ctx.author.id, premio)
        mensagem = (
            "🎉 **JACKPOT!!!**\n"
            f"💰 +**{premio} pontos**"
        )

    elif (
        resultado[0] == resultado[1]
        or resultado[1] == resultado[2]
        or resultado[0] == resultado[2]
    ):
        premio = 60
        add_points(ctx.author.id, premio)
        mensagem = (
            "😎 **DOIS IGUAIS!**\n"
            f"💰 +**{premio} pontos**"
        )

    else:
        mensagem = "💀 **Perdeu KKKKK**"

    await ctx.send(
        f"🎰 **SLOT MACHINE**\n\n"
        f"┃ {' | '.join(resultado)} ┃\n\n"
        f"{mensagem}"
    )


# =========================================================
# 🎲 APOSTA
# =========================================================

@bot.command()
async def aposta(ctx, valor: int = None):

    if valor is None:
        await ctx.send("🎲 Use `!aposta 100`")
        return

    if valor <= 0:
        await ctx.send("❌ Valor inválido.")
        return

    saldo = get_pontos(ctx.author.id)

    if saldo < valor:
        await ctx.send(
            f"❌ Você só tem **{saldo} pontos**."
        )
        return

    dado = random.randint(1, 6)

    if dado >= 5:

        premio = valor * 2

        add_points(
            ctx.author.id,
            premio
        )

        await ctx.send(
            f"🎲 Você rolou **{dado}**!\n"
            f"🔥 **GANHOU!**\n"
            f"💰 +**{premio} pontos**"
        )

    else:

        add_points(
            ctx.author.id,
            -valor
        )

        await ctx.send(
            f"🎲 Você rolou **{dado}**!\n"
            f"💀 **PERDEU!**\n"
            f"📉 -**{valor} pontos**"
        )


# =========================================================
# 🪙 CARA OU COROA
# =========================================================

@bot.command()
async def caraoucoroa(
    ctx,
    valor: int = None,
    escolha: str = None
):

    if valor is None or escolha is None:

        await ctx.send(
            "🪙 Use:\n"
            "`!caraoucoroa 100 cara`\n\n"
            "Escolhas: `cara` ou `coroa`"
        )

        return

    escolha = escolha.lower()

    if escolha not in ["cara", "coroa"]:

        await ctx.send(
            "❌ Escolha `cara` ou `coroa`."
        )

        return

    if valor <= 0:

        await ctx.send(
            "❌ Valor inválido."
        )

        return

    saldo = get_pontos(ctx.author.id)

    if saldo < valor:

        await ctx.send(
            f"❌ Você só tem **{saldo} pontos**."
        )

        return

    resultado = random.choice(
        ["cara", "coroa"]
    )

    if resultado == escolha:

        premio = valor * 2

        add_points(
            ctx.author.id,
            premio
        )

        await ctx.send(
            f"🪙 Caiu **{resultado}**!\n"
            f"🎉 **ACERTOU!**\n"
            f"💰 +**{premio} pontos**"
        )

    else:

        add_points(
            ctx.author.id,
            -valor
        )

        await ctx.send(
            f"🪙 Caiu **{resultado}**!\n"
            f"💀 **ERROU!**\n"
            f"📉 -**{valor} pontos**"
        )


# =========================================================
# 🐀 RATADA
# =========================================================

@bot.command()
async def ratada(ctx):

    eventos = [
        ("🐀 Você encontrou uma carteira no esgoto!", 100),
        ("🐀 Um rato gigante te deu uma moeda!", 50),
        ("🐀 Você achou um PIX de R$5!", 150),
        ("🐀 Rato lambeu seu bumbum...", -50),
        ("🐀 O prefeito dos ratos te recompensou!", 300),
        ("🐀 Você caiu dentro de uma lata de lixo!", -100),
        ("🐀 VOCÊ ENCONTROU O TESOURO DOS RATOS!", 500),
        ("🐀 Você foi roubado por um rato menor que você!", -75)
    ]

    evento, recompensa = random.choice(eventos)

    add_points(
        ctx.author.id,
        recompensa
    )

    await ctx.send(
        f"🐀 **RATADA!**\n\n"
        f"{evento}\n\n"
        f"{'🎉' if recompensa > 0 else '💀'} "
        f"**{recompensa:+} pontos**"
    )
# =========================================================
# ⚔️ BRIGA
# =========================================================

@bot.command()
async def briga(
    ctx,
    pessoa: discord.Member = None,
    valor: int = None
):

    if pessoa is None or valor is None:
        await ctx.send(
            "⚔️ Use assim:\n"
            "`!briga @pessoa 100`"
        )
        return

    if pessoa == ctx.author:
        await ctx.send(
            "💀 Você não pode brigar consigo mesmo KKKKK."
        )
        return

    if pessoa.bot:
        await ctx.send(
            "🤖 Você não pode brigar com um bot."
        )
        return

    if valor <= 0:
        await ctx.send(
            "❌ A aposta precisa ser maior que 0."
        )
        return

    saldo1 = get_pontos(ctx.author.id)
    saldo2 = get_pontos(pessoa.id)

    if saldo1 < valor:
        await ctx.send(
            f"❌ Você não tem **{valor} pontos**."
        )
        return

    if saldo2 < valor:
        await ctx.send(
            f"❌ **{pessoa.display_name}** não tem "
            f"**{valor} pontos**."
        )
        return

    vencedor = random.choice(
        [ctx.author, pessoa]
    )

    perdedor = (
        pessoa
        if vencedor == ctx.author
        else ctx.author
    )

    add_points(
        perdedor.id,
        -valor
    )

    add_points(
        vencedor.id,
        valor
    )

    game_result(vencedor.id, "win")
    game_result(perdedor.id, "loss")

    add_xp(vencedor.id, 25)
    add_xp(perdedor.id, 10)

    await ctx.send(
        f"⚔️ **BRIGA DOS RATOS!**\n\n"
        f"🥊 {ctx.author.display_name} VS "
        f"{pessoa.display_name}\n\n"
        f"🏆 **Vencedor:** {vencedor.display_name}\n"
        f"💰 Ganhou **{valor} pontos**!\n\n"
        f"💀 {perdedor.display_name} perdeu "
        f"**{valor} pontos**."
    )


# =========================================================
# 🎮 JOGO DA VELHA
# =========================================================

@bot.command()
async def velha(
    ctx,
    pessoa: discord.Member = None
):

    if pessoa is None:
        await ctx.send(
            "❌ Use: `!velha @pessoa`"
        )
        return

    if pessoa == ctx.author:
        await ctx.send(
            "❌ Você não pode jogar contra você mesmo."
        )
        return

    if pessoa.bot:
        await ctx.send(
            "❌ Você não pode jogar contra um bot."
        )
        return

    chave = ctx.channel.id

    if chave in jogos:
        await ctx.send(
            "❌ Já existe uma partida de velha neste canal."
        )
        return

    jogos[chave] = {
        "jogador1": ctx.author.id,
        "jogador2": pessoa.id,
        "vez": ctx.author.id,
        "tabuleiro": [" "] * 9
    }

    await mostrar_velha(ctx)


async def mostrar_velha(ctx):

    jogo = jogos[ctx.channel.id]

    tabuleiro = jogo["tabuleiro"]

    texto = (
        f"```text\n"
        f" {tabuleiro[0]} | {tabuleiro[1]} | {tabuleiro[2]}\n"
        f"---+---+---\n"
        f" {tabuleiro[3]} | {tabuleiro[4]} | {tabuleiro[5]}\n"
        f"---+---+---\n"
        f" {tabuleiro[6]} | {tabuleiro[7]} | {tabuleiro[8]}\n"
        f"```\n"
    )

    vez = ctx.guild.get_member(
        jogo["vez"]
    )

    await ctx.send(
        f"⭕ **JOGO DA VELHA**\n\n"
        f"{texto}"
        f"Vez de: **{vez.display_name}**\n\n"
        f"Use `!jogar 1` até `!jogar 9`."
    )


@bot.command()
async def jogar(ctx, posicao: int = None):

    chave = ctx.channel.id

    if chave not in jogos:
        await ctx.send(
            "❌ Não existe uma partida ativa."
        )
        return

    jogo = jogos[chave]

    if ctx.author.id != jogo["vez"]:
        await ctx.send(
            "❌ Não é sua vez."
        )
        return

    if posicao is None or posicao < 1 or posicao > 9:
        await ctx.send(
            "❌ Escolha uma posição de 1 a 9."
        )
        return

    indice = posicao - 1

    if jogo["tabuleiro"][indice] != " ":
        await ctx.send(
            "❌ Essa posição já está ocupada."
        )
        return

    simbolo = (
        "❌"
        if ctx.author.id == jogo["jogador1"]
        else "⭕"
    )

    jogo["tabuleiro"][indice] = simbolo

    combinacoes = [
        (0, 1, 2),
        (3, 4, 5),
        (6, 7, 8),
        (0, 3, 6),
        (1, 4, 7),
        (2, 5, 8),
        (0, 4, 8),
        (2, 4, 6)
    ]

    vencedor = None

    for a, b, c in combinacoes:

        if (
            jogo["tabuleiro"][a] == simbolo
            and jogo["tabuleiro"][b] == simbolo
            and jogo["tabuleiro"][c] == simbolo
        ):
            vencedor = ctx.author
            break

    if vencedor:

        add_points(
            vencedor.id,
            50
        )

        add_xp(
            vencedor.id,
            50
        )

        game_result(
            vencedor.id,
            "win"
        )

        outro_id = (
            jogo["jogador2"]
            if vencedor.id == jogo["jogador1"]
            else jogo["jogador1"]
        )

        game_result(
            outro_id,
            "loss"
        )

        del jogos[chave]

        await ctx.send(
            f"🏆 **{vencedor.display_name} VENCEU!**\n\n"
            f"💰 **+50 pontos**\n"
            f"⭐ **+50 XP**"
        )

        return

    if " " not in jogo["tabuleiro"]:

        game_result(
            jogo["jogador1"],
            "draw"
        )

        game_result(
            jogo["jogador2"],
            "draw"
        )

        del jogos[chave]

        await ctx.send(
            "🤝 **EMPATE!**\n"
            "Ninguém ganhou pontos."
        )

        return

    jogo["vez"] = (
        jogo["jogador2"]
        if ctx.author.id == jogo["jogador1"]
        else jogo["jogador1"]
    )

    await mostrar_velha(ctx)


# =========================================================
# 😈 FORCA
# =========================================================

PALAVRAS_FORCA = [
    "python",
    "discord",
    "rato",
    "minecraft",
    "fortnite",
    "valorant",
    "futebol",
    "computador",
    "teclado",
    "mouse",
    "internet",
    "servidor",
    "amizade",
    "jogador",
    "windows"
]


@bot.command()
async def forca(ctx):

    chave = ctx.channel.id

    if chave in jogos:
        await ctx.send(
            "❌ Já existe um jogo ativo neste canal."
        )
        return

    palavra = random.choice(
        PALAVRAS_FORCA
    )

    jogos[chave] = {
        "tipo": "forca",
        "palavra": palavra,
        "letras": [],
        "tentativas": 6,
        "jogador": ctx.author.id
    }

    await mostrar_forca(ctx)


async def mostrar_forca(ctx):

    jogo = jogos[ctx.channel.id]

    palavra = jogo["palavra"]

    letras = jogo["letras"]

    exibicao = ""

    for letra in palavra:

        if letra in letras:
            exibicao += letra + " "

        else:
            exibicao += "_ "

    await ctx.send(
        f"😈 **FORCA**\n\n"
        f"Palavra: **{exibicao}**\n"
        f"❤️ Tentativas: **{jogo['tentativas']}**\n\n"
        f"Use `!letra a`"
    )


@bot.command()
async def letra(ctx, tentativa: str = None):

    chave = ctx.channel.id

    if chave not in jogos:
        await ctx.send(
            "❌ Não existe uma forca ativa."
        )
        return

    jogo = jogos[chave]

    if jogo.get("tipo") != "forca":
        await ctx.send(
            "❌ Esse canal está usando outro jogo."
        )
        return

    if ctx.author.id != jogo["jogador"]:
        await ctx.send(
            "❌ Quem iniciou a forca deve jogar."
        )
        return

    if tentativa is None or len(tentativa) != 1:
        await ctx.send(
            "❌ Digite apenas uma letra.\n"
            "Exemplo: `!letra a`"
        )
        return

    tentativa = tentativa.lower()

    if not tentativa.isalpha():
        await ctx.send(
            "❌ Digite uma letra."
        )
        return

    if tentativa in jogo["letras"]:
        await ctx.send(
            "❌ Você já tentou essa letra."
        )
        return

    jogo["letras"].append(tentativa)

    if tentativa not in jogo["palavra"]:
        jogo["tentativas"] -= 1

        if jogo["tentativas"] <= 0:

            palavra = jogo["palavra"]

            game_result(
                ctx.author.id,
                "loss"
            )

            del jogos[chave]

            await ctx.send(
                f"💀 **VOCÊ PERDEU!**\n\n"
                f"A palavra era **{palavra}**."
            )

            return

    venceu = all(
        letra in jogo["letras"]
        for letra in jogo["palavra"]
    )

    if venceu:

        add_points(
            ctx.author.id,
            30
        )

        add_xp(
            ctx.author.id,
            30
        )

        game_result(
            ctx.author.id,
            "win"
        )

        del jogos[chave]

        await ctx.send(
            "🎉 **VOCÊ VENCEU A FORCA!**\n\n"
            "💰 **+30 pontos**\n"
            "⭐ **+30 XP**"
        )

        return

    await mostrar_forca(ctx)


# =========================================================
# 🔢 ADIVINHE O NÚMERO
# =========================================================

@bot.command()
async def adivinhe(ctx):

    chave = ctx.channel.id

    if chave in jogos:
        await ctx.send(
            "❌ Já existe um jogo ativo neste canal."
        )
        return

    numero = random.randint(
        1,
        100
    )

    jogos[chave] = {
        "tipo": "adivinhe",
        "numero": numero,
        "tentativas": 0,
        "jogador": ctx.author.id
    }

    await ctx.send(
        "🔢 **ADIVINHE O NÚMERO!**\n\n"
        "Pensei em um número entre **1 e 100**.\n"
        "Use `!chute 50`."
    )


@bot.command()
async def chute(ctx, numero: int = None):

    chave = ctx.channel.id

    if chave not in jogos:
        await ctx.send(
            "❌ Não existe um jogo de adivinhação."
        )
        return

    jogo = jogos[chave]

    if jogo.get("tipo") != "adivinhe":
        await ctx.send(
            "❌ Esse canal está usando outro jogo."
        )
        return

    if ctx.author.id != jogo["jogador"]:
        await ctx.send(
            "❌ Quem iniciou o jogo deve jogar."
        )
        return

    if numero is None or numero < 1 or numero > 100:
        await ctx.send(
            "❌ Escolha um número entre 1 e 100."
        )
        return

    jogo["tentativas"] += 1

    numero_certo = jogo["numero"]

    if numero == numero_certo:

        tentativas = jogo["tentativas"]

        premio = max(
            10,
            100 - ((tentativas - 1) * 10)
        )

        add_points(
            ctx.author.id,
            premio
        )

        add_xp(
            ctx.author.id,
            25
        )

        game_result(
            ctx.author.id,
            "win"
        )

        del jogos[chave]

        await ctx.send(
            f"🎉 **ACERTOU!**\n\n"
            f"🔢 Número: **{numero_certo}**\n"
            f"🎯 Tentativas: **{tentativas}**\n"
            f"💰 **+{premio} pontos**"
        )

        return

    if numero < numero_certo:

        await ctx.send(
            "⬆️ É **MAIOR**!"
        )

    else:

        await ctx.send(
            "⬇️ É **MENOR**!"
        )


# =========================================================
# ✂️ PEDRA PAPEL TESOURA
# =========================================================

@bot.command()
async def ppt(ctx, escolha: str = None):

    if escolha is None:

        await ctx.send(
            "✂️ Use:\n"
            "`!ppt pedra`\n"
            "`!ppt papel`\n"
            "`!ppt tesoura`"
        )

        return

    escolha = escolha.lower()

    opcoes = [
        "pedra",
        "papel",
        "tesoura"
    ]

    if escolha not in opcoes:

        await ctx.send(
            "❌ Escolha pedra, papel ou tesoura."
        )

        return

    bot_escolha = random.choice(opcoes)

    if escolha == bot_escolha:

        resultado = "draw"

        mensagem = "🤝 **EMPATE!**"

    elif (
        (escolha == "pedra" and bot_escolha == "tesoura")
        or
        (escolha == "papel" and bot_escolha == "pedra")
        or
        (escolha == "tesoura" and bot_escolha == "papel")
    ):

        resultado = "win"

        mensagem = (
            "🎉 **VOCÊ GANHOU!**\n"
            "💰 **+10 pontos**"
        )

        add_points(
            ctx.author.id,
            10
        )

        add_xp(
            ctx.author.id,
            10
        )

    else:

        resultado = "loss"

        mensagem = "💀 **VOCÊ PERDEU!**"

    game_result(
        ctx.author.id,
        resultado
    )

    await ctx.send(
        f"✂️ **PEDRA, PAPEL OU TESOURA**\n\n"
        f"👤 Você: **{escolha}**\n"
        f"🤖 Bot: **{bot_escolha}**\n\n"
        f"{mensagem}"
    )


# =========================================================
# 🧠 QUIZ
# =========================================================

QUIZ = [
    {
        "pergunta": "Qual é a capital do Brasil?",
        "opcoes": ["A) São Paulo", "B) Brasília", "C) Rio de Janeiro", "D) Salvador"],
        "resposta": "B"
    },
    {
        "pergunta": "Quantos planetas existem no Sistema Solar?",
        "opcoes": ["A) 7", "B) 8", "C) 9", "D) 10"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o maior planeta do Sistema Solar?",
        "opcoes": ["A) Terra", "B) Saturno", "C) Júpiter", "D) Netuno"],
        "resposta": "C"
    },
    {
        "pergunta": "Qual planeta é conhecido como Planeta Vermelho?",
        "opcoes": ["A) Marte", "B) Vênus", "C) Mercúrio", "D) Saturno"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é o maior oceano da Terra?",
        "opcoes": ["A) Atlântico", "B) Índico", "C) Ártico", "D) Pacífico"],
        "resposta": "D"
    },
    {
        "pergunta": "Qual é o menor país do mundo?",
        "opcoes": ["A) Mônaco", "B) Vaticano", "C) Malta", "D) Andorra"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o maior país do mundo em território?",
        "opcoes": ["A) Canadá", "B) China", "C) Rússia", "D) Brasil"],
        "resposta": "C"
    },
    {
        "pergunta": "Qual é o maior país da América do Sul?",
        "opcoes": ["A) Argentina", "B) Brasil", "C) Peru", "D) Chile"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o idioma oficial do Brasil?",
        "opcoes": ["A) Espanhol", "B) Português", "C) Inglês", "D) Italiano"],
        "resposta": "B"
    },
    {
        "pergunta": "Quantos estados o Brasil possui?",
        "opcoes": ["A) 24", "B) 25", "C) 26", "D) 27"],
        "resposta": "C"
    },
    {
        "pergunta": "Qual é o maior órgão do corpo humano?",
        "opcoes": ["A) Coração", "B) Pele", "C) Fígado", "D) Pulmão"],
        "resposta": "B"
    },
    {
        "pergunta": "Quantos ossos aproximadamente possui um adulto?",
        "opcoes": ["A) 106", "B) 206", "C) 306", "D) 406"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual órgão bombeia o sangue pelo corpo?",
        "opcoes": ["A) Pulmão", "B) Cérebro", "C) Coração", "D) Fígado"],
        "resposta": "C"
    },
    {
        "pergunta": "Qual é o símbolo químico do ouro?",
        "opcoes": ["A) Ag", "B) Au", "C) Fe", "D) Go"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o símbolo químico da prata?",
        "opcoes": ["A) Ag", "B) Au", "C) Pt", "D) Pr"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é a fórmula da água?",
        "opcoes": ["A) CO2", "B) O2", "C) H2O", "D) H2"],
        "resposta": "C"
    },
    {
        "pergunta": "Qual gás os seres humanos precisam respirar?",
        "opcoes": ["A) Oxigênio", "B) Hélio", "C) Hidrogênio", "D) Metano"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é o satélite natural da Terra?",
        "opcoes": ["A) Marte", "B) Lua", "C) Sol", "D) Vênus"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual estrela está no centro do Sistema Solar?",
        "opcoes": ["A) Sirius", "B) Sol", "C) Polaris", "D) Vega"],
        "resposta": "B"
    },
    {
        "pergunta": "Quantos lados tem um triângulo?",
        "opcoes": ["A) 2", "B) 3", "C) 4", "D) 5"],
        "resposta": "B"
    },
    {
        "pergunta": "Quantos lados tem um quadrado?",
        "opcoes": ["A) 3", "B) 4", "C) 5", "D) 6"],
        "resposta": "B"
    },
    {
        "pergunta": "Quanto é 7 × 8?",
        "opcoes": ["A) 54", "B) 56", "C) 58", "D) 64"],
        "resposta": "B"
    },
    {
        "pergunta": "Quanto é 100 ÷ 4?",
        "opcoes": ["A) 20", "B) 25", "C) 30", "D) 40"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é a raiz quadrada de 81?",
        "opcoes": ["A) 7", "B) 8", "C) 9", "D) 10"],
        "resposta": "C"
    },
    {
        "pergunta": "Qual é o resultado de 12 × 12?",
        "opcoes": ["A) 124", "B) 132", "C) 144", "D) 154"],
        "resposta": "C"
    },
    {
        "pergunta": "Quem escreveu Dom Quixote?",
        "opcoes": ["A) Machado de Assis", "B) Miguel de Cervantes", "C) Shakespeare", "D) Camões"],
        "resposta": "B"
    },
    {
        "pergunta": "Quem escreveu Romeu e Julieta?",
        "opcoes": ["A) Shakespeare", "B) Cervantes", "C) Dante", "D) Homero"],
        "resposta": "A"
    },
    {
        "pergunta": "Quem escreveu O Pequeno Príncipe?",
        "opcoes": ["A) Antoine de Saint-Exupéry", "B) Tolkien", "C) J.K. Rowling", "D) George Orwell"],
        "resposta": "A"
    },
    {
        "pergunta": "Quem pintou a Mona Lisa?",
        "opcoes": ["A) Van Gogh", "B) Picasso", "C) Leonardo da Vinci", "D) Michelangelo"],
        "resposta": "C"
    },
    {
        "pergunta": "Qual é a língua mais falada no mundo por número de falantes nativos?",
        "opcoes": ["A) Inglês", "B) Espanhol", "C) Mandarim", "D) Português"],
        "resposta": "C"
    },
    {
        "pergunta": "Qual país é conhecido como Terra do Sol Nascente?",
        "opcoes": ["A) China", "B) Japão", "C) Coreia do Sul", "D) Tailândia"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é a capital da França?",
        "opcoes": ["A) Paris", "B) Lyon", "C) Marselha", "D) Nice"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é a capital da Argentina?",
        "opcoes": ["A) Córdoba", "B) Rosário", "C) Buenos Aires", "D) Mendoza"],
        "resposta": "C"
    },
    {
        "pergunta": "Qual é a capital do Chile?",
        "opcoes": ["A) Lima", "B) Santiago", "C) Quito", "D) Bogotá"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é a capital do Japão?",
        "opcoes": ["A) Osaka", "B) Kyoto", "C) Tóquio", "D) Hiroshima"],
        "resposta": "C"
    },
    {
        "pergunta": "Qual é a capital dos Estados Unidos?",
        "opcoes": ["A) Nova York", "B) Washington, D.C.", "C) Los Angeles", "D) Chicago"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o animal terrestre mais rápido?",
        "opcoes": ["A) Leão", "B) Guepardo", "C) Cavalo", "D) Lobo"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o maior animal do planeta?",
        "opcoes": ["A) Elefante", "B) Baleia-azul", "C) Girafa", "D) Tubarão-branco"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual animal é conhecido como rei da selva?",
        "opcoes": ["A) Tigre", "B) Leão", "C) Onça", "D) Leopardo"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o maior mamífero terrestre?",
        "opcoes": ["A) Rinoceronte", "B) Hipopótamo", "C) Elefante", "D) Girafa"],
        "resposta": "C"
    },
    {
        "pergunta": "Qual ave é conhecida por não voar e viver na Antártida?",
        "opcoes": ["A) Pinguim", "B) Águia", "C) Gaivota", "D) Albatroz"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual esporte é jogado com uma bola laranja e uma cesta?",
        "opcoes": ["A) Futebol", "B) Basquete", "C) Vôlei", "D) Handebol"],
        "resposta": "B"
    },
    {
        "pergunta": "Quantos jogadores cada time possui em campo no futebol?",
        "opcoes": ["A) 9", "B) 10", "C) 11", "D) 12"],
        "resposta": "C"
    },
    {
        "pergunta": "Qual país venceu a Copa do Mundo de 2022?",
        "opcoes": ["A) Brasil", "B) França", "C) Argentina", "D) Alemanha"],
        "resposta": "C"
    },
    {
        "pergunta": "Qual país sediou a Copa do Mundo de 2014?",
        "opcoes": ["A) Brasil", "B) Rússia", "C) Alemanha", "D) África do Sul"],
        "resposta": "A"
    },
    {
        "pergunta": "Quantos minutos possui uma partida normal de futebol?",
        "opcoes": ["A) 60", "B) 70", "C) 80", "D) 90"],
        "resposta": "D"
    },
    {
        "pergunta": "Qual clube é conhecido como Tricolor Gaúcho?",
        "opcoes": ["A) Internacional", "B) Grêmio", "C) Juventude", "D) Caxias"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual clube brasileiro é conhecido como Colorado?",
        "opcoes": ["A) Grêmio", "B) Internacional", "C) Flamengo", "D) Santos"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o nome do estádio do Grêmio?",
        "opcoes": ["A) Beira-Rio", "B) Maracanã", "C) Arena do Grêmio", "D) Mineirão"],
        "resposta": "C"
    },
    {
        "pergunta": "Qual é o nome do estádio do Internacional?",
        "opcoes": ["A) Beira-Rio", "B) Arena do Grêmio", "C) Morumbi", "D) Pacaembu"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual jogo pertence à franquia Grand Theft Auto?",
        "opcoes": ["A) GTA V", "B) FIFA 23", "C) Valorant", "D) Minecraft"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual empresa criou Minecraft?",
        "opcoes": ["A) Rockstar", "B) Mojang", "C) Valve", "D) Epic Games"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual empresa criou Fortnite?",
        "opcoes": ["A) Epic Games", "B) Valve", "C) Mojang", "D) Ubisoft"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual empresa criou GTA?",
        "opcoes": ["A) Rockstar Games", "B) EA", "C) Ubisoft", "D) Activision"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual empresa criou Counter-Strike?",
        "opcoes": ["A) Valve", "B) Riot Games", "C) Epic Games", "D) Ubisoft"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual empresa criou Valorant?",
        "opcoes": ["A) Riot Games", "B) Valve", "C) Rockstar", "D) EA"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual jogo possui o modo Battle Royale chamado Warzone?",
        "opcoes": ["A) Call of Duty", "B) Battlefield", "C) GTA", "D) Minecraft"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual jogo possui personagens como Mario e Luigi?",
        "opcoes": ["A) Sonic", "B) Mario", "C) Zelda", "D) Pokémon"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o mascote famoso da Nintendo que usa boné vermelho?",
        "opcoes": ["A) Luigi", "B) Mario", "C) Sonic", "D) Link"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual personagem é famoso por ser um ouriço azul?",
        "opcoes": ["A) Sonic", "B) Mario", "C) Pikachu", "D) Kirby"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual Pokémon é conhecido por ser amarelo?",
        "opcoes": ["A) Charmander", "B) Pikachu", "C) Squirtle", "D) Bulbasaur"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o elemento químico representado por Fe?",
        "opcoes": ["A) Ferro", "B) Flúor", "C) Fósforo", "D) Frâncio"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é o elemento químico representado por O?",
        "opcoes": ["A) Ouro", "B) Oxigênio", "C) Ósmio", "D) Ozônio"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o planeta mais próximo do Sol?",
        "opcoes": ["A) Vênus", "B) Terra", "C) Mercúrio", "D) Marte"],
        "resposta": "C"
    },
    {
        "pergunta": "Qual planeta possui os famosos anéis?",
        "opcoes": ["A) Saturno", "B) Marte", "C) Vênus", "D) Mercúrio"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é a temperatura aproximada de congelamento da água em Celsius?",
        "opcoes": ["A) 0°C", "B) 10°C", "C) 50°C", "D) 100°C"],
        "resposta": "A"
    },
    {
        "pergunta": "A que temperatura a água ferve ao nível do mar?",
        "opcoes": ["A) 50°C", "B) 75°C", "C) 100°C", "D) 120°C"],
        "resposta": "C"
    },
    {
        "pergunta": "Qual instrumento mede a temperatura?",
        "opcoes": ["A) Barômetro", "B) Termômetro", "C) Velocímetro", "D) Altímetro"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual instrumento mede a pressão atmosférica?",
        "opcoes": ["A) Barômetro", "B) Termômetro", "C) Balança", "D) Cronômetro"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é a velocidade aproximada da luz no vácuo?",
        "opcoes": ["A) 30 mil km/s", "B) 300 mil km/s", "C) 3 milhões km/s", "D) 3 mil km/s"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual continente possui o Brasil?",
        "opcoes": ["A) Europa", "B) América do Sul", "C) África", "D) Ásia"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o maior continente do mundo?",
        "opcoes": ["A) África", "B) Europa", "C) Ásia", "D) América"],
        "resposta": "C"
    },
    {
        "pergunta": "Qual é o menor continente?",
        "opcoes": ["A) Europa", "B) Oceania", "C) África", "D) América do Sul"],
        "resposta": "B"
    },
    {
        "pergunta": "Em qual continente fica o Egito?",
        "opcoes": ["A) África", "B) Ásia", "C) Europa", "D) América"],
        "resposta": "A"
    },
    {
        "pergunta": "Em qual continente fica o Japão?",
        "opcoes": ["A) Europa", "B) Ásia", "C) África", "D) Oceania"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o maior deserto quente do mundo?",
        "opcoes": ["A) Gobi", "B) Saara", "C) Atacama", "D) Kalahari"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o rio mais famoso por atravessar o Egito?",
        "opcoes": ["A) Amazonas", "B) Nilo", "C) Mississippi", "D) Danúbio"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o maior rio em volume de água do mundo?",
        "opcoes": ["A) Nilo", "B) Amazonas", "C) Paraná", "D) Yangtzé"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é a capital do Rio Grande do Sul?",
        "opcoes": ["A) Caxias do Sul", "B) Canoas", "C) Porto Alegre", "D) Pelotas"],
        "resposta": "C"
    },
    {
        "pergunta": "Qual é a capital de Santa Catarina?",
        "opcoes": ["A) Florianópolis", "B) Joinville", "C) Blumenau", "D) Chapecó"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é a capital do Paraná?",
        "opcoes": ["A) Londrina", "B) Curitiba", "C) Maringá", "D) Cascavel"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é a capital de Minas Gerais?",
        "opcoes": ["A) Belo Horizonte", "B) Uberlândia", "C) Juiz de Fora", "D) Ouro Preto"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é a capital da Bahia?",
        "opcoes": ["A) Salvador", "B) Feira de Santana", "C) Ilhéus", "D) Porto Seguro"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é a capital de Pernambuco?",
        "opcoes": ["A) Olinda", "B) Recife", "C) Caruaru", "D) Jaboatão"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o menor estado brasileiro em área?",
        "opcoes": ["A) Alagoas", "B) Sergipe", "C) Espírito Santo", "D) Rio de Janeiro"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o maior estado brasileiro em área?",
        "opcoes": ["A) Pará", "B) Amazonas", "C) Mato Grosso", "D) Bahia"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é a moeda oficial do Brasil?",
        "opcoes": ["A) Peso", "B) Real", "C) Dólar", "D) Cruzeiro"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é a moeda dos Estados Unidos?",
        "opcoes": ["A) Euro", "B) Dólar", "C) Libra", "D) Peso"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é a moeda do Japão?",
        "opcoes": ["A) Yuan", "B) Won", "C) Iene", "D) Dólar"],
        "resposta": "C"
    },
    {
        "pergunta": "Qual é a moeda oficial da União Europeia?",
        "opcoes": ["A) Libra", "B) Euro", "C) Dólar", "D) Franco"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o metal mais usado na fabricação de fios elétricos?",
        "opcoes": ["A) Ferro", "B) Cobre", "C) Ouro", "D) Prata"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o planeta conhecido por ter vida confirmada?",
        "opcoes": ["A) Marte", "B) Terra", "C) Vênus", "D) Júpiter"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o processo pelo qual plantas produzem seu alimento?",
        "opcoes": ["A) Respiração", "B) Fotossíntese", "C) Digestão", "D) Fermentação"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual gás as plantas absorvem durante a fotossíntese?",
        "opcoes": ["A) Oxigênio", "B) Nitrogênio", "C) Gás carbônico", "D) Hélio"],
        "resposta": "C"
    },
    {
        "pergunta": "Qual gás é liberado pelas plantas na fotossíntese?",
        "opcoes": ["A) Oxigênio", "B) Gás carbônico", "C) Hidrogênio", "D) Hélio"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é a principal fonte de energia da Terra?",
        "opcoes": ["A) Lua", "B) Sol", "C) Vento", "D) Oceanos"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o nome do processo de transformação de líquido em gás?",
        "opcoes": ["A) Condensação", "B) Evaporação", "C) Solidificação", "D) Fusão"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o processo de transformação de gás em líquido?",
        "opcoes": ["A) Condensação", "B) Evaporação", "C) Fusão", "D) Sublimação"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é o processo de transformação de sólido em líquido?",
        "opcoes": ["A) Fusão", "B) Condensação", "C) Evaporação", "D) Sublimação"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é o processo de transformação de líquido em sólido?",
        "opcoes": ["A) Evaporação", "B) Solidificação", "C) Fusão", "D) Condensação"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o maior felino das Américas?",
        "opcoes": ["A) Leão", "B) Onça-pintada", "C) Puma", "D) Jaguatirica"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual animal é famoso por mudar de cor?",
        "opcoes": ["A) Camaleão", "B) Elefante", "C) Cavalo", "D) Leão"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual animal produz mel?",
        "opcoes": ["A) Mosca", "B) Abelha", "C) Formiga", "D) Borboleta"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o inseto conhecido por produzir seda?",
        "opcoes": ["A) Bicho-da-seda", "B) Abelha", "C) Formiga", "D) Besouro"],
        "resposta": "A"
    },
    {
        "pergunta": "Quantos dias possui um ano comum?",
        "opcoes": ["A) 360", "B) 365", "C) 366", "D) 370"],
        "resposta": "B"
    },
    {
        "pergunta": "Quantos dias possui um ano bissexto?",
        "opcoes": ["A) 364", "B) 365", "C) 366", "D) 367"],
        "resposta": "C"
    },
    {
        "pergunta": "Quantos meses possui um ano?",
        "opcoes": ["A) 10", "B) 11", "C) 12", "D) 13"],
        "resposta": "C"
    },
    {
        "pergunta": "Quantas horas possui um dia?",
        "opcoes": ["A) 12", "B) 18", "C) 24", "D) 48"],
        "resposta": "C"
    },
    {
        "pergunta": "Quantos minutos possui uma hora?",
        "opcoes": ["A) 30", "B) 45", "C) 60", "D) 90"],
        "resposta": "C"
    },
    {
        "pergunta": "Quantos segundos possui um minuto?",
        "opcoes": ["A) 30", "B) 45", "C) 60", "D) 100"],
        "resposta": "C"
    },
    {
        "pergunta": "Qual é o primeiro mês do ano?",
        "opcoes": ["A) Janeiro", "B) Fevereiro", "C) Março", "D) Dezembro"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é o último mês do ano?",
        "opcoes": ["A) Outubro", "B) Novembro", "C) Dezembro", "D) Janeiro"],
        "resposta": "C"
    },
    {
        "pergunta": "Qual é a cor resultante da mistura de azul e amarelo?",
        "opcoes": ["A) Verde", "B) Roxo", "C) Laranja", "D) Rosa"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é a cor resultante da mistura de vermelho e azul?",
        "opcoes": ["A) Verde", "B) Roxo", "C) Laranja", "D) Amarelo"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é a cor resultante da mistura de vermelho e amarelo?",
        "opcoes": ["A) Azul", "B) Roxo", "C) Laranja", "D) Verde"],
        "resposta": "C"
    },
    {
        "pergunta": "Qual é o idioma oficial da Argentina?",
        "opcoes": ["A) Português", "B) Espanhol", "C) Inglês", "D) Italiano"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o idioma oficial de Portugal?",
        "opcoes": ["A) Espanhol", "B) Português", "C) Francês", "D) Inglês"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é a capital de Portugal?",
        "opcoes": ["A) Porto", "B) Lisboa", "C) Coimbra", "D) Braga"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é a capital da Itália?",
        "opcoes": ["A) Milão", "B) Roma", "C) Veneza", "D) Nápoles"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é a capital da Alemanha?",
        "opcoes": ["A) Munique", "B) Frankfurt", "C) Berlim", "D) Hamburgo"],
        "resposta": "C"
    },
    {
        "pergunta": "Qual é a capital da Espanha?",
        "opcoes": ["A) Barcelona", "B) Madrid", "C) Sevilha", "D) Valência"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é a capital da Inglaterra?",
        "opcoes": ["A) Manchester", "B) Liverpool", "C) Londres", "D) Birmingham"],
        "resposta": "C"
    },
    {
        "pergunta": "Qual é o maior país da América do Norte?",
        "opcoes": ["A) México", "B) Canadá", "C) Estados Unidos", "D) Cuba"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o país conhecido pela Torre Eiffel?",
        "opcoes": ["A) Itália", "B) França", "C) Espanha", "D) Alemanha"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual país possui a cidade de Nova York?",
        "opcoes": ["A) Canadá", "B) Estados Unidos", "C) México", "D) Brasil"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o nome da maior floresta tropical do mundo?",
        "opcoes": ["A) Amazônia", "B) Mata Atlântica", "C) Taiga", "D) Congo"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual bioma brasileiro é conhecido por suas grandes áreas alagadas?",
        "opcoes": ["A) Cerrado", "B) Pantanal", "C) Caatinga", "D) Pampa"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual bioma predomina no Rio Grande do Sul?",
        "opcoes": ["A) Pampa", "B) Caatinga", "C) Amazônia", "D) Pantanal"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é o maior bioma brasileiro?",
        "opcoes": ["A) Cerrado", "B) Amazônia", "C) Caatinga", "D) Pampa"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é a capital do Uruguai?",
        "opcoes": ["A) Punta del Este", "B) Montevidéu", "C) Colônia", "D) Salto"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é a capital do Paraguai?",
        "opcoes": ["A) Assunção", "B) Ciudad del Este", "C) Encarnación", "D) Luque"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é a capital do Peru?",
        "opcoes": ["A) Cusco", "B) Lima", "C) Arequipa", "D) Trujillo"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é a capital da Colômbia?",
        "opcoes": ["A) Medellín", "B) Cali", "C) Bogotá", "D) Cartagena"],
        "resposta": "C"
    },
    {
        "pergunta": "Qual é a capital do Equador?",
        "opcoes": ["A) Quito", "B) Guayaquil", "C) Cuenca", "D) Loja"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é a capital da Venezuela?",
        "opcoes": ["A) Maracaibo", "B) Caracas", "C) Valencia", "D) Barquisimeto"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o nome do oceano entre a América e a Europa?",
        "opcoes": ["A) Pacífico", "B) Atlântico", "C) Índico", "D) Ártico"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o oceano entre a África e a Austrália?",
        "opcoes": ["A) Índico", "B) Atlântico", "C) Pacífico", "D) Ártico"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é o maior oceano do planeta?",
        "opcoes": ["A) Atlântico", "B) Pacífico", "C) Índico", "D) Ártico"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o continente mais frio?",
        "opcoes": ["A) Europa", "B) Ásia", "C) Antártida", "D) América"],
        "resposta": "C"
    },
    {
        "pergunta": "Qual é o continente conhecido por ser o berço da humanidade?",
        "opcoes": ["A) África", "B) Europa", "C) Ásia", "D) América"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é o nome do satélite natural de Marte?",
        "opcoes": ["A) Lua", "B) Fobos", "C) Titã", "D) Europa"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é a maior lua de Saturno?",
        "opcoes": ["A) Europa", "B) Titã", "C) Fobos", "D) Lua"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual planeta é conhecido por possuir a Grande Mancha Vermelha?",
        "opcoes": ["A) Marte", "B) Júpiter", "C) Saturno", "D) Netuno"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual planeta é o mais distante do Sol entre os oito?",
        "opcoes": ["A) Urano", "B) Netuno", "C) Saturno", "D) Júpiter"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o nome da galáxia onde está o Sistema Solar?",
        "opcoes": ["A) Andrômeda", "B) Via Láctea", "C) Sombrero", "D) Triângulo"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é a unidade básica da vida?",
        "opcoes": ["A) Átomo", "B) Célula", "C) Tecido", "D) Órgão"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual molécula carrega informações genéticas?",
        "opcoes": ["A) DNA", "B) Água", "C) Glicose", "D) Oxigênio"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é a vitamina produzida pela exposição ao Sol?",
        "opcoes": ["A) Vitamina A", "B) Vitamina B", "C) Vitamina C", "D) Vitamina D"],
        "resposta": "D"
    },
    {
        "pergunta": "Qual órgão é responsável principalmente pela respiração?",
        "opcoes": ["A) Coração", "B) Pulmões", "C) Fígado", "D) Rins"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual órgão filtra o sangue e produz urina?",
        "opcoes": ["A) Rins", "B) Pulmões", "C) Coração", "D) Estômago"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual órgão é responsável pela digestão inicial dos alimentos?",
        "opcoes": ["A) Estômago", "B) Pulmão", "C) Coração", "D) Rim"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é o maior músculo do corpo humano?",
        "opcoes": ["A) Bíceps", "B) Glúteo máximo", "C) Tríceps", "D) Panturrilha"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o osso mais longo do corpo humano?",
        "opcoes": ["A) Fêmur", "B) Tíbia", "C) Úmero", "D) Rádio"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é o maior planeta rochoso do Sistema Solar?",
        "opcoes": ["A) Terra", "B) Marte", "C) Vênus", "D) Mercúrio"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual planeta é conhecido como Estrela d'Alva?",
        "opcoes": ["A) Vênus", "B) Marte", "C) Júpiter", "D) Mercúrio"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é o único planeta conhecido por ter água líquida abundante na superfície?",
        "opcoes": ["A) Marte", "B) Terra", "C) Vênus", "D) Mercúrio"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o maior vulcão conhecido do Sistema Solar?",
        "opcoes": ["A) Vesúvio", "B) Monte Olimpo", "C) Etna", "D) Mauna Loa"],
        "resposta": "B"
    },
    {
        "pergunta": "Em qual planeta fica o Monte Olimpo?",
        "opcoes": ["A) Marte", "B) Terra", "C) Vênus", "D) Júpiter"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é o nome do processo em que uma substância passa diretamente do sólido para o gás?",
        "opcoes": ["A) Fusão", "B) Sublimação", "C) Condensação", "D) Solidificação"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o principal componente do ar atmosférico?",
        "opcoes": ["A) Oxigênio", "B) Nitrogênio", "C) Gás carbônico", "D) Hidrogênio"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o símbolo químico do sódio?",
        "opcoes": ["A) S", "B) Na", "C) So", "D) Sd"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o símbolo químico do carbono?",
        "opcoes": ["A) C", "B) Ca", "C) Co", "D) Cr"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é o símbolo químico do hidrogênio?",
        "opcoes": ["A) H", "B) He", "C) Hy", "D) Hg"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é o símbolo químico do potássio?",
        "opcoes": ["A) P", "B) Po", "C) K", "D) Pt"],
        "resposta": "C"
    },
    {
        "pergunta": "Qual é o metal líquido em temperatura ambiente?",
        "opcoes": ["A) Ferro", "B) Mercúrio", "C) Cobre", "D) Alumínio"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é a fórmula do gás carbônico?",
        "opcoes": ["A) CO", "B) CO2", "C) C2O", "D) O2C"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é a fórmula do oxigênio molecular?",
        "opcoes": ["A) O", "B) O2", "C) O3", "D) Ox"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o pH aproximado de uma solução neutra?",
        "opcoes": ["A) 0", "B) 5", "C) 7", "D) 14"],
        "resposta": "C"
    },
    {
        "pergunta": "Qual é a substância responsável pela acidez do estômago?",
        "opcoes": ["A) Ácido clorídrico", "B) Ácido sulfúrico", "C) Ácido nítrico", "D) Ácido acético"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é o nome popular do ácido acético diluído?",
        "opcoes": ["A) Álcool", "B) Vinagre", "C) Água sanitária", "D) Gasolina"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o combustível usado pela maioria dos carros a gasolina?",
        "opcoes": ["A) Gasolina", "B) Água", "C) Oxigênio", "D) Nitrogênio"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é a marca de carros conhecida pelo modelo Civic?",
        "opcoes": ["A) Honda", "B) Toyota", "C) BMW", "D) Ford"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual marca fabrica o modelo Corolla?",
        "opcoes": ["A) Honda", "B) Toyota", "C) Chevrolet", "D) Volkswagen"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual marca fabrica o modelo Mustang?",
        "opcoes": ["A) Ford", "B) Chevrolet", "C) Dodge", "D) BMW"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual marca fabrica o modelo Golf?",
        "opcoes": ["A) Volkswagen", "B) Ford", "C) Honda", "D) Toyota"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual empresa fabrica veículos BMW?",
        "opcoes": ["A) BMW Group", "B) Volkswagen", "C) Toyota", "D) Mercedes-Benz"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual marca é conhecida pelo símbolo das quatro argolas?",
        "opcoes": ["A) BMW", "B) Audi", "C) Mercedes-Benz", "D) Volvo"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual marca é conhecida pela estrela de três pontas?",
        "opcoes": ["A) Audi", "B) BMW", "C) Mercedes-Benz", "D) Lexus"],
        "resposta": "C"
    },
    {
        "pergunta": "Qual marca é conhecida por seu logotipo azul e branco em formato circular?",
        "opcoes": ["A) BMW", "B) Audi", "C) Porsche", "D) Volvo"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é a capital da Rússia?",
        "opcoes": ["A) Moscou", "B) São Petersburgo", "C) Kiev", "D) Minsk"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é a capital da China?",
        "opcoes": ["A) Xangai", "B) Pequim", "C) Hong Kong", "D) Shenzhen"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é a capital da Coreia do Sul?",
        "opcoes": ["A) Busan", "B) Seul", "C) Incheon", "D) Daegu"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é a capital da Austrália?",
        "opcoes": ["A) Sydney", "B) Melbourne", "C) Canberra", "D) Brisbane"],
        "resposta": "C"
    },
    {
        "pergunta": "Qual é a capital do Canadá?",
        "opcoes": ["A) Toronto", "B) Vancouver", "C) Ottawa", "D) Montreal"],
        "resposta": "C"
    },
    {
        "pergunta": "Qual é a capital do México?",
        "opcoes": ["A) Cancún", "B) Cidade do México", "C) Guadalajara", "D) Monterrey"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o maior país da América do Sul em população?",
        "opcoes": ["A) Argentina", "B) Brasil", "C) Colômbia", "D) Peru"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é a capital do Paraguai?",
        "opcoes": ["A) Assunção", "B) Ciudad del Este", "C) Pedro Juan Caballero", "D) Encarnación"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é a capital do Uruguai?",
        "opcoes": ["A) Salto", "B) Montevidéu", "C) Rivera", "D) Maldonado"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o nome do maior estádio de futebol do Brasil em capacidade aproximada?",
        "opcoes": ["A) Maracanã", "B) Arena do Grêmio", "C) Beira-Rio", "D) Mineirão"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é o esporte mais popular do Brasil?",
        "opcoes": ["A) Basquete", "B) Futebol", "C) Tênis", "D) Vôlei"],
        "resposta": "B"
    },
    {
        "pergunta": "Quantas Copas do Mundo a seleção brasileira masculina venceu até 2022?",
        "opcoes": ["A) 3", "B) 4", "C) 5", "D) 6"],
        "resposta": "C"
    },
    {
        "pergunta": "Qual país ganhou a primeira Copa do Mundo?",
        "opcoes": ["A) Brasil", "B) Uruguai", "C) Argentina", "D) Itália"],
        "resposta": "B"
    },
    {
        "pergunta": "Em que ano aconteceu a primeira Copa do Mundo?",
        "opcoes": ["A) 1920", "B) 1930", "C) 1940", "D) 1950"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual jogador é conhecido como Rei do Futebol?",
        "opcoes": ["A) Pelé", "B) Romário", "C) Ronaldo", "D) Zico"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual jogador brasileiro é conhecido como Fenômeno?",
        "opcoes": ["A) Ronaldinho", "B) Ronaldo", "C) Kaká", "D) Rivaldo"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual jogador argentino é conhecido como um dos maiores da história?",
        "opcoes": ["A) Messi", "B) Di María", "C) Agüero", "D) Tévez"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é a capital da Espanha?",
        "opcoes": ["A) Barcelona", "B) Madrid", "C) Valência", "D) Sevilha"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual clube é conhecido como Mengão?",
        "opcoes": ["A) Flamengo", "B) Vasco", "C) Fluminense", "D) Botafogo"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual clube é conhecido como Timão?",
        "opcoes": ["A) Palmeiras", "B) Corinthians", "C) Santos", "D) São Paulo"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual clube é conhecido como Verdão?",
        "opcoes": ["A) Palmeiras", "B) Corinthians", "C) Santos", "D) Cruzeiro"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual clube é conhecido como Peixe?",
        "opcoes": ["A) Santos", "B) São Paulo", "C) Flamengo", "D) Palmeiras"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é o maior estádio do Rio Grande do Sul?",
        "opcoes": ["A) Arena do Grêmio", "B) Beira-Rio", "C) Olímpico", "D) Alfredo Jaconi"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual cidade é conhecida como capital do Rio Grande do Sul?",
        "opcoes": ["A) Canoas", "B) Porto Alegre", "C) Caxias do Sul", "D) Pelotas"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o nome do estado brasileiro cuja capital é Porto Alegre?",
        "opcoes": ["A) Santa Catarina", "B) Paraná", "C) Rio Grande do Sul", "D) São Paulo"],
        "resposta": "C"
    },
    {
        "pergunta": "Qual estado brasileiro faz fronteira com Argentina e Uruguai?",
        "opcoes": ["A) Rio Grande do Sul", "B) Paraná", "C) Santa Catarina", "D) Mato Grosso"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual estado brasileiro faz fronteira com o Paraguai e o Paraná?",
        "opcoes": ["A) Mato Grosso do Sul", "B) Goiás", "C) São Paulo", "D) Minas Gerais"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é o maior estado da Região Sul em área?",
        "opcoes": ["A) Paraná", "B) Santa Catarina", "C) Rio Grande do Sul", "D) Os três têm a mesma área"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual estado é conhecido pela cidade de Florianópolis?",
        "opcoes": ["A) Paraná", "B) Santa Catarina", "C) Rio Grande do Sul", "D) São Paulo"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual estado é conhecido pela cidade de Curitiba?",
        "opcoes": ["A) Paraná", "B) Santa Catarina", "C) Rio Grande do Sul", "D) São Paulo"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é o maior planeta gasoso do Sistema Solar?",
        "opcoes": ["A) Saturno", "B) Júpiter", "C) Urano", "D) Netuno"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual planeta gira de lado devido à sua inclinação extrema?",
        "opcoes": ["A) Marte", "B) Urano", "C) Júpiter", "D) Mercúrio"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual planeta tem os ventos mais rápidos do Sistema Solar?",
        "opcoes": ["A) Terra", "B) Netuno", "C) Marte", "D) Vênus"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o planeta mais quente do Sistema Solar?",
        "opcoes": ["A) Mercúrio", "B) Vênus", "C) Marte", "D) Júpiter"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual planeta possui o maior sistema de anéis?",
        "opcoes": ["A) Saturno", "B) Júpiter", "C) Urano", "D) Netuno"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é o nome da nossa estrela?",
        "opcoes": ["A) Sirius", "B) Sol", "C) Vega", "D) Polaris"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é a força que mantém os planetas em órbita?",
        "opcoes": ["A) Magnetismo", "B) Gravidade", "C) Eletricidade", "D) Atrito"],
        "resposta": "B"
    },
    {
        "pergunta": "Quem formulou as leis do movimento e da gravitação universal?",
        "opcoes": ["A) Einstein", "B) Newton", "C) Galileu", "D) Darwin"],
        "resposta": "B"
    },
    {
        "pergunta": "Quem desenvolveu a teoria da relatividade?",
        "opcoes": ["A) Newton", "B) Einstein", "C) Tesla", "D) Darwin"],
        "resposta": "B"
    },
    {
        "pergunta": "Quem é conhecido pela teoria da evolução por seleção natural?",
        "opcoes": ["A) Darwin", "B) Einstein", "C) Newton", "D) Pasteur"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual cientista é associado à invenção da lâmpada elétrica comercial?",
        "opcoes": ["A) Thomas Edison", "B) Newton", "C) Einstein", "D) Darwin"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual inventor é famoso pelo desenvolvimento do sistema de corrente alternada?",
        "opcoes": ["A) Nikola Tesla", "B) Newton", "C) Darwin", "D) Pasteur"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é a unidade de medida de força no SI?",
        "opcoes": ["A) Joule", "B) Newton", "C) Watt", "D) Pascal"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é a unidade de potência?",
        "opcoes": ["A) Watt", "B) Newton", "C) Joule", "D) Volt"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é a unidade de energia no SI?",
        "opcoes": ["A) Watt", "B) Joule", "C) Newton", "D) Ampere"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é a unidade de corrente elétrica?",
        "opcoes": ["A) Volt", "B) Ampere", "C) Ohm", "D) Watt"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é a unidade de resistência elétrica?",
        "opcoes": ["A) Volt", "B) Ohm", "C) Ampere", "D) Watt"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual é o nome dado à conexão mundial de computadores?",
        "opcoes": ["A) Internet", "B) Bluetooth", "C) HDMI", "D) USB"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual empresa desenvolveu o Windows?",
        "opcoes": ["A) Apple", "B) Microsoft", "C) Google", "D) Intel"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual empresa desenvolveu o Android?",
        "opcoes": ["A) Google", "B) Microsoft", "C) Apple", "D) Intel"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual empresa desenvolveu o iPhone?",
        "opcoes": ["A) Samsung", "B) Apple", "C) Google", "D) Nokia"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual empresa desenvolveu o processador Ryzen?",
        "opcoes": ["A) Intel", "B) AMD", "C) NVIDIA", "D) Qualcomm"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual empresa fabrica as placas de vídeo GeForce RTX?",
        "opcoes": ["A) AMD", "B) NVIDIA", "C) Intel", "D) ASUS"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual empresa fabrica as placas de vídeo Radeon?",
        "opcoes": ["A) AMD", "B) NVIDIA", "C) Intel", "D) Microsoft"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual componente é responsável principalmente pelo processamento gráfico?",
        "opcoes": ["A) GPU", "B) SSD", "C) RAM", "D) Fonte"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual componente armazena temporariamente dados usados pelos programas?",
        "opcoes": ["A) RAM", "B) SSD", "C) GPU", "D) Fonte"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual componente fornece energia para o computador?",
        "opcoes": ["A) RAM", "B) Fonte de alimentação", "C) SSD", "D) CPU"],
        "resposta": "B"
    },
    {
        "pergunta": "O que significa CPU?",
        "opcoes": ["A) Central Processing Unit", "B) Computer Power Unit", "C) Central Program Utility", "D) Computer Processing Utility"],
        "resposta": "A"
    },
    {
        "pergunta": "O que significa GPU?",
        "opcoes": ["A) Graphics Processing Unit", "B) General Processing Utility", "C) Graphics Power Unit", "D) Game Processing Unit"],
        "resposta": "A"
    },
    {
        "pergunta": "O que significa RAM?",
        "opcoes": ["A) Random Access Memory", "B) Rapid Access Machine", "C) Random Application Memory", "D) Read Access Memory"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual formato é comum para imagens com transparência?",
        "opcoes": ["A) PNG", "B) TXT", "C) MP3", "D) EXE"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual formato é usado normalmente para músicas?",
        "opcoes": ["A) PNG", "B) MP3", "C) JPG", "D) TXT"],
        "resposta": "B"
    },
    {
        "pergunta": "Qual formato é usado normalmente para vídeos?",
        "opcoes": ["A) MP4", "B) MP3", "C) PNG", "D) TXT"],
        "resposta": "A"
    },
    {
        "pergunta": "Qual é a linguagem usada neste bot?",
        "opcoes": ["A) Python", "B) Java", "C) C#", "D) PHP"],
        "resposta": "A"
    }
]


# =========================================================
# SISTEMA ANTI-REPETIÇÃO DO QUIZ
# =========================================================

def proximo_quiz(guild_id):

    guild_id = str(guild_id)

    if guild_id not in quiz_usadas:
        quiz_usadas[guild_id] = []

    usadas = quiz_usadas[guild_id]

    disponiveis = [
        i
        for i in range(len(QUIZ))
        if i not in usadas
    ]

    if not disponiveis:

        quiz_usadas[guild_id] = []
        usadas = []
        disponiveis = list(
            range(len(QUIZ))
        )

    indice = random.choice(disponiveis)

    quiz_usadas[guild_id].append(indice)

    salvar_json(
        QUIZ_USADAS_FILE,
        quiz_usadas
    )

    return QUIZ[indice]


@bot.command()
async def quiz(ctx):

    chave = ctx.channel.id

    if chave in quiz_ativos:
        await ctx.send(
            "🧠 Já existe um quiz ativo neste canal!"
        )
        return

    pergunta = proximo_quiz(
        ctx.guild.id
    )

    quiz_ativos[chave] = {
        "pergunta": pergunta,
        "autor": ctx.author.id
    }

    texto = "\n".join(
        pergunta["opcoes"]
    )

    await ctx.send(
        f"🧠 **QUIZ DOS RATOS**\n\n"
        f"❓ **{pergunta['pergunta']}**\n\n"
        f"{texto}\n\n"
        f"Responda usando:\n"
        f"`!responder A`"
    )


@bot.command()
async def responder(ctx, resposta: str = None):

    chave = ctx.channel.id

    if chave not in quiz_ativos:
        await ctx.send("❌ Não existe um quiz ativo neste canal.")
        return

    jogo = quiz_ativos[chave]
    pergunta = jogo["pergunta"]

    if resposta is None:
        await ctx.send(
            "❌ Use `!responder A`, `!responder B`, `!responder C` ou `!responder D`."
        )
        return

    resposta = resposta.strip().upper()

    if resposta not in ("A", "B", "C", "D"):
        await ctx.send("❌ Resposta inválida. Use apenas A, B, C ou D.")
        return

    resposta_correta = str(pergunta["resposta"]).strip().upper()

    print(f"[QUIZ] Resposta: {resposta}")
    print(f"[QUIZ] Correta: {resposta_correta}")

    if resposta == resposta_correta:

        add_points(ctx.author.id, 10)
        add_xp(ctx.author.id, 10)

        game_result(
            ctx.author.id,
            "win"
        )

        del quiz_ativos[chave]

        await ctx.send(
            "🎉 **ACERTOU!**\n\n"
            "💰 **+10 pontos**\n"
            "⭐ **+10 XP**"
        )

    else:

        game_result(
            ctx.author.id,
            "loss"
        )

        del quiz_ativos[chave]

        await ctx.send(
            f"💀 **ERROU!**\n\n"
            f"A resposta correta era **{resposta_correta}**."
        )

# =========================================================
# 🎲 DADO
# =========================================================

@bot.command()
async def dado(ctx):

    numero = random.randint(
        1,
        6
    )

    await ctx.send(
        f"🎲 **{ctx.author.display_name}** "
        f"rolou o dado!\n"
        f"Resultado: **{numero}**"
    )


# =========================================================
# 🪙 MOEDA
# =========================================================

@bot.command()
async def moeda(ctx):

    resultado = random.choice(
        [
            "🪙 Cara",
            "🪙 Coroa"
        ]
    )

    await ctx.send(
        f"**{ctx.author.display_name}** "
        f"jogou a moeda!\n"
        f"Resultado: **{resultado}**"
    )


# =========================================================
# 🎱 8BALL
# =========================================================

@bot.command(name="8ball")
async def eightball(
    ctx,
    *,
    pergunta=None
):

    respostas = [
        "🎱 Com certeza!",
        "🎱 Sem dúvidas.",
        "🎱 Provavelmente.",
        "🎱 Talvez...",
        "🎱 Acho que não.",
        "🎱 Nem ferrando KKKKK.",
        "🎱 O futuro dirá.",
        "🎱 Melhor não perguntar isso."
    ]

    if pergunta is None:

        await ctx.send(
            "🎱 Faça uma pergunta!\n"
            "Exemplo: `!8ball vou ganhar hoje?`"
        )

        return

    resposta = random.choice(
        respostas
    )

    await ctx.send(
        f"🎱 **Pergunta:** {pergunta}\n"
        f"**Resposta:** {resposta}"
    )


# =========================================================
# 💘 SHIP
# =========================================================

@bot.command()
async def ship(
    ctx,
    pessoa1: discord.Member = None,
    pessoa2: discord.Member = None
):

    if pessoa1 is None or pessoa2 is None:

        await ctx.send(
            "💘 Use: `!ship @pessoa1 @pessoa2`"
        )

        return

    porcentagem = random.randint(
        0,
        100
    )

    await ctx.send(
        f"💘 **COMPATIBILIDADE**\n\n"
        f"{pessoa1.display_name} ❤️ "
        f"{pessoa2.display_name}\n\n"
        f"💗 **{porcentagem}%**"
    )


# =========================================================
# 🏳️‍🌈 GAYMETRO
# =========================================================

@bot.command()
async def gaymetro(
    ctx,
    pessoa: discord.Member = None
):

    if pessoa is None:
        pessoa = ctx.author

    porcentagem = random.randint(
        0,
        100
    )

    await ctx.send(
        f"🏳️‍🌈 **Gaymetro de "
        f"{pessoa.display_name}**\n\n"
        f"Resultado: **{porcentagem}%**"
    )


# =========================================================
# 🖼️ AVATAR
# =========================================================

@bot.command()
async def avatar(
    ctx,
    pessoa: discord.Member = None
):

    if pessoa is None:
        pessoa = ctx.author

    embed = discord.Embed(
        title=f"🖼️ Avatar de "
               f"{pessoa.display_name}"
    )

    embed.set_image(
        url=pessoa.display_avatar.url
    )

    await ctx.send(
        embed=embed
    )


# =========================================================
# 📊 SERVER
# =========================================================

@bot.command()
async def server(ctx):

    servidor = ctx.guild

    embed = discord.Embed(
        title=f"📊 {servidor.name}",
        description="Informações do servidor"
    )

    embed.add_field(
        name="👥 Membros",
        value=servidor.member_count
    )

    embed.add_field(
        name="🆔 ID",
        value=servidor.id
    )

    embed.add_field(
        name="👑 Dono",
        value=servidor.owner
    )

    await ctx.send(
        embed=embed
    )


# =========================================================
# 🏓 PING
# =========================================================

@bot.command()
async def ping(ctx):

    latencia = round(
        bot.latency * 1000
    )

    await ctx.send(
        f"🏓 Pong!\n"
        f"📡 **{latencia}ms**"
    )


# =========================================================
# ❓ AJUDA
# =========================================================

@bot.command()
async def ajuda(ctx):

    embed = discord.Embed(
        title="🐀 BOT DOS RATOS",
        description="Lista de comandos"
    )

    embed.add_field(
        name="💰 Economia",
        value=(
            "`!pontos`\n"
            "`!ranking`\n"
            "`!loja`\n"
            "`!comprar 1`\n"
            "`!inventario`"
        ),
        inline=False
    )

    embed.add_field(
        name="🎮 Jogos",
        value=(
            "`!slot`\n"
            "`!aposta 100`\n"
            "`!caraoucoroa 100 cara`\n"
            "`!briga @pessoa 100`\n"
            "`!velha @pessoa`\n"
            "`!forca`\n"
            "`!adivinhe`\n"
            "`!ppt pedra`\n"
            "`!quiz`"
        ),
        inline=False
    )

    embed.add_field(
        name="🐀 Diversão",
        value=(
            "`!ratada`\n"
            "`!dado`\n"
            "`!moeda`\n"
            "`!8ball pergunta`\n"
            "`!ship @p1 @p2`\n"
            "`!gaymetro`\n"
            "`!avatar`\n"
            "`!server`\n"
            "`!ping`"
        ),
        inline=False
    )

    embed.add_field(
        name="👤 Perfil",
        value="`!perfil`",
        inline=False
    )

    embed.add_field(
        name="🧠 Quiz",
        value=(
            "`!quiz`\n"
            "`!responder A`"
        ),
        inline=False
    )

    await ctx.send(
        embed=embed
    )


# =========================================================
# ❌ ERROS DOS COMANDOS
# =========================================================

@bot.event
async def on_command_error(
    ctx,
    error
):

    if isinstance(
        error,
        commands.CommandNotFound
    ):
        return

    if isinstance(
        error,
        commands.MissingRequiredArgument
    ):
        await ctx.send(
            "❌ Está faltando alguma informação no comando."
        )
        return

    if isinstance(
        error,
        commands.BadArgument
    ):
        await ctx.send(
            "❌ Não consegui entender algum argumento."
        )
        return

    if isinstance(
        error,
        commands.MissingPermissions
    ):
        await ctx.send(
            "❌ Você não tem permissão para usar esse comando."
        )
        return

    if isinstance(error, discord.HTTPException):
        print(f"[DISCORD HTTP] {error}")
        try:
            await ctx.send("❌ O Discord recusou a mensagem. Verifique o limite de 2.000 caracteres ou tente novamente.")
        except discord.HTTPException:
            pass
        return

    print(f"Erro no comando: {error}")


# =========================================================
# SERVIDOR WEB PARA O RENDER
# =========================================================

app = Flask(__name__)

@app.route("/")
def home():
    return "🐀 Bot dos Ratos está online!"

def iniciar_servidor_web():
    porta = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=porta)


# =========================================================
# INICIAR BOT
# =========================================================

if not TOKEN:
    raise RuntimeError(
        "A variável DISCORD_TOKEN não foi configurada no Render."
    )

threading.Thread(target=iniciar_servidor_web, daemon=True).start()
bot.run(TOKEN)

