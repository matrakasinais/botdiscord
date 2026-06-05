# ============================================================
#  GAMEBOOST PREMIUM - Bot Discord Completo
#  Instalar: pip install discord.py aiohttp
#  Rodar: python gameboost_bot.py
# ============================================================

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import json
import os
import random
import string
import aiohttp
from datetime import datetime, timedelta

# ============================================================
#  CONFIGURACOES - variaveis de ambiente (nunca coloque tokens no codigo!)
# ============================================================
TOKEN        = os.environ["DISCORD_TOKEN"]               # Definir no Railway / .env local
ADMIN_ID     = int(os.environ.get("ADMIN_ID", "279638596195975178"))
SHEETS_URL   = os.environ.get("SHEETS_URL", "https://script.google.com/macros/s/AKfycbzzSOBl_xQA1-GAJpAynHocKdcciv3o6wGZiO3Gct7EcmMLaYNsv7HFqoZHDfiF6FoktQ/exec")
EXE_PATH     = os.path.join(os.path.dirname(__file__), "GameBoost_Premium.exe")

# Planos disponiveis
PLANOS = {
    "mensal"   : {"dias": 30,  "preco": "R$ 19,90", "nome": "PREMIUM Mensal"},
    "trimestral": {"dias": 90, "preco": "R$ 44,90", "nome": "PREMIUM Trimestral"},
    "vitalicio": {"dias": 0,   "preco": "R$ 34,90", "nome": "PREMIUM Vitalicio"},
}

# Cores
COR_LARANJA  = 0xFF6D00
COR_VERDE    = 0x00E676
COR_VERMELHO = 0xFF3C50
COR_AZUL     = 0x00B4DC

# ============================================================
#  FUNCOES AUXILIARES
# ============================================================
def gerar_chave():
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "-".join("".join(random.choices(chars, k=5)) for _ in range(4))

async def registrar_licenca_sheets(cliente: str, plano: str, chave: str):
    """Registra a licenca no Google Sheets via Apps Script"""
    try:
        params = {
            "action"  : "criar",
            "cliente" : cliente,
            "plano"   : plano,
            "chave"   : chave,
            "dias"    : PLANOS.get(plano, {}).get("dias", 30)
        }
        url = SHEETS_URL + "?" + "&".join(f"{k}={v}" for k,v in params.items())
        async with aiohttp.ClientSession() as session:
            async with session.get(url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                result = await resp.json(content_type=None)
                return result.get("success", False)
    except Exception as e:
        print(f"Erro ao registrar no Sheets: {e}")
        return False

async def validar_licenca_api(chave: str):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{SHEETS_URL}?action=validate&key={chave}", allow_redirects=True, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                return await resp.json(content_type=None)
    except:
        return {"valid": False, "msg": "Erro de conexao"}

# ============================================================
#  BOT SETUP
# ============================================================
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ============================================================
#  SETUP COMPLETO DO SERVIDOR
# ============================================================
@bot.command(name="setup")
async def setup_server(ctx):
    if ctx.author.id != ADMIN_ID:
        return await ctx.send("Sem permissao.")

    msg = await ctx.send("⚙️ Configurando servidor GameBoost...")
    guild = ctx.guild

    # ── CARGOS ──────────────────────────────────────────────
    await msg.edit(content="🔧 Criando cargos...")

    cargos = {
        "👑 Dono"           : {"color": discord.Color.from_rgb(255,109,0),  "hoist": True,  "perms": discord.Permissions.all()},
        "🛡️ Admin"          : {"color": discord.Color.from_rgb(255,60,80),   "hoist": True,  "perms": discord.Permissions.all()},
        "⚡ Suporte"        : {"color": discord.Color.from_rgb(0,180,220),   "hoist": True,  "perms": discord.Permissions(manage_messages=True, view_channel=True)},
        "💎 PREMIUM Vitalicio": {"color": discord.Color.from_rgb(255,200,0),"hoist": True,  "perms": discord.Permissions(view_channel=True)},
        "🥇 PREMIUM Mensal" : {"color": discord.Color.from_rgb(255,109,0),  "hoist": True,  "perms": discord.Permissions(view_channel=True)},
        "✅ Cliente"        : {"color": discord.Color.from_rgb(0,230,118),   "hoist": False, "perms": discord.Permissions(view_channel=True)},
        "👤 Visitante"      : {"color": discord.Color.default(),             "hoist": False, "perms": discord.Permissions(view_channel=True)},
    }

    cargo_map = {}
    for nome, cfg in cargos.items():
        existing = discord.utils.get(guild.roles, name=nome)
        if not existing:
            r = await guild.create_role(name=nome, color=cfg["color"], hoist=cfg["hoist"], permissions=cfg["perms"])
        else:
            r = existing
        cargo_map[nome] = r

    # ── CATEGORIAS E CANAIS ──────────────────────────────────
    await msg.edit(content="📁 Criando canais...")

    # Permissoes base
    everyone = guild.default_role
    premium_roles = [cargo_map["💎 PREMIUM Vitalicio"], cargo_map["🥇 PREMIUM Mensal"], cargo_map["✅ Cliente"]]
    admin_roles   = [cargo_map["👑 Dono"], cargo_map["🛡️ Admin"]]

    ow_read    = {everyone: discord.PermissionOverwrite(view_channel=True, send_messages=False)}
    ow_premium = {everyone: discord.PermissionOverwrite(view_channel=False)}
    for r in premium_roles + admin_roles:
        ow_premium[r] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
    ow_admin = {everyone: discord.PermissionOverwrite(view_channel=False)}
    for r in admin_roles:
        ow_admin[r] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

    estrutura = [
        {
            "categoria": "━━━━━ GAMEBOOST ━━━━━",
            "perms": ow_read,
            "canais": []
        },
        {
            "categoria": "📢 INFORMACOES",
            "perms": ow_read,
            "canais": [
                {"nome": "📌boas-vindas",      "tipo": "text",  "perms": ow_read},
                {"nome": "📋regras",            "tipo": "text",  "perms": ow_read},
                {"nome": "🔥novidades",         "tipo": "text",  "perms": ow_read},
                {"nome": "📊status-do-bot",     "tipo": "text",  "perms": ow_read},
            ]
        },
        {
            "categoria": "🛒 VENDAS",
            "perms": ow_read,
            "canais": [
                {"nome": "💰planos-e-precos",   "tipo": "text",  "perms": ow_read},
                {"nome": "🎟️comprar-licenca",   "tipo": "text",  "perms": ow_read},
                {"nome": "✅como-ativar",        "tipo": "text",  "perms": ow_read},
            ]
        },
        {
            "categoria": "💬 COMUNIDADE",
            "perms": None,
            "canais": [
                {"nome": "💬geral",             "tipo": "text",  "perms": None},
                {"nome": "🎮games",             "tipo": "text",  "perms": None},
                {"nome": "📸resultados-boost",  "tipo": "text",  "perms": None},
                {"nome": "🔊geral-voz",         "tipo": "voice", "perms": None},
            ]
        },
        {
            "categoria": "⚡ AREA PREMIUM",
            "perms": ow_premium,
            "canais": [
                {"nome": "🚀download-gameboost","tipo": "text",  "perms": ow_premium},
                {"nome": "🔑minhas-licencas",   "tipo": "text",  "perms": ow_premium},
                {"nome": "💡dicas-exclusivas",  "tipo": "text",  "perms": ow_premium},
                {"nome": "🔊premium-voz",       "tipo": "voice", "perms": ow_premium},
            ]
        },
        {
            "categoria": "🎫 SUPORTE",
            "perms": ow_read,
            "canais": [
                {"nome": "📩abrir-ticket",      "tipo": "text",  "perms": ow_read},
            ]
        },
        {
            "categoria": "🔧 ADMIN",
            "perms": ow_admin,
            "canais": [
                {"nome": "📊logs-tickets",      "tipo": "text",  "perms": ow_admin},
                {"nome": "🔑gerenciar-licencas","tipo": "text",  "perms": ow_admin},
                {"nome": "📈vendas",            "tipo": "text",  "perms": ow_admin},
                {"nome": "⚙️bot-comandos",      "tipo": "text",  "perms": ow_admin},
            ]
        },
    ]

    canal_map = {}
    for bloco in estrutura:
        cat_name = bloco["categoria"]
        existing_cat = discord.utils.get(guild.categories, name=cat_name)
        if existing_cat:
            cat = existing_cat
        else:
            cat_ow = bloco["perms"] if bloco["perms"] else {}
            cat = await guild.create_category(cat_name, overwrites=cat_ow)

        for ch in bloco["canais"]:
            existing_ch = discord.utils.get(guild.channels, name=ch["nome"].replace("📌","").replace("📋","").replace("🔥","").replace("📊","").replace("💰","").replace("🎟️","").replace("✅","").replace("💬","").replace("🎮","").replace("📸","").replace("🔊","").replace("🚀","").replace("🔑","").replace("💡","").replace("🎫","").replace("📩","").replace("🔧","").replace("📈","").replace("⚙️","").strip())
            ch_ow = ch["perms"] if ch["perms"] else {}
            if ch["tipo"] == "voice":
                if not existing_ch:
                    c = await guild.create_voice_channel(ch["nome"], category=cat, overwrites=ch_ow)
            else:
                if not existing_ch:
                    c = await guild.create_text_channel(ch["nome"], category=cat, overwrites=ch_ow)
                    canal_map[ch["nome"]] = c

    await msg.edit(content="📝 Enviando mensagens nos canais...")

    # ── MENSAGEM BOAS VINDAS ─────────────────────────────────
    ch = discord.utils.get(guild.text_channels, name="📌boas-vindas")
    if ch:
        embed = discord.Embed(
            title="⚡ BEM-VINDO AO GAMEBOOST PREMIUM",
            description=(
                "O **otimizador gamer profissional** para Windows.\n\n"
                "Maximize o desempenho do seu PC para jogos com um clique.\n\n"
                "**O que o GameBoost faz:**\n"
                "✅ Libera núcleos da CPU\n"
                "✅ Otimiza GPU (NVIDIA/AMD)\n"
                "✅ Desativa serviços pesados\n"
                "✅ Limpa RAM e temporários\n"
                "✅ Ativa Ultimate Performance\n"
                "✅ Game Mode otimizado\n\n"
                "**Navegue pelos canais e adquira sua licença!**"
            ),
            color=COR_LARANJA
        )
        embed.set_footer(text="GAMEBOOST PREMIUM • Otimizador Gamer Profissional")
        await ch.send(embed=embed)

    # ── MENSAGEM REGRAS ──────────────────────────────────────
    ch = discord.utils.get(guild.text_channels, name="📋regras")
    if ch:
        embed = discord.Embed(title="📋 REGRAS DO SERVIDOR", color=COR_LARANJA)
        embed.add_field(name="1️⃣ Respeito", value="Trate todos com respeito. Sem ofensas ou discriminação.", inline=False)
        embed.add_field(name="2️⃣ Sem spam", value="Não envie mensagens repetidas ou links sem autorização.", inline=False)
        embed.add_field(name="3️⃣ Canal correto", value="Use o canal adequado para cada assunto.", inline=False)
        embed.add_field(name="4️⃣ Licenças", value="Cada licença é pessoal e intransferível. Não compartilhe.", inline=False)
        embed.add_field(name="5️⃣ Suporte", value="Abra um ticket em 📩abrir-ticket para qualquer problema.", inline=False)
        await ch.send(embed=embed)

    # ── MENSAGEM PLANOS ──────────────────────────────────────
    ch = discord.utils.get(guild.text_channels, name="💰planos-e-precos")
    if ch:
        embed = discord.Embed(
            title="💰 PLANOS GAMEBOOST PREMIUM",
            description="Escolha o plano ideal para você:",
            color=COR_LARANJA
        )
        embed.add_field(
            name="🥇 MENSAL — R$ 19,90",
            value="✅ Acesso por 30 dias\n✅ Todas as otimizações\n✅ Suporte via ticket\n✅ Atualizações inclusas",
            inline=True
        )
        embed.add_field(
            name="💎 VITALICIO — R$ 49,90",
            value="✅ Acesso permanente\n✅ Todas as otimizações\n✅ Suporte prioritário\n✅ Todas as atualizações para sempre",
            inline=True
        )
        embed.add_field(
            name="📲 Como comprar",
            value="Vá em 🎟️comprar-licenca e siga as instruções.\nPagamento via PIX, cartão ou boleto.",
            inline=False
        )
        await ch.send(embed=embed)

    # ── MENSAGEM COMPRAR ─────────────────────────────────────
    ch = discord.utils.get(guild.text_channels, name="🎟️comprar-licenca")
    if ch:
        embed = discord.Embed(
            title="🎟️ COMPRAR LICENÇA GAMEBOOST",
            description="Siga os passos abaixo para adquirir sua licença:",
            color=COR_VERDE
        )
        embed.add_field(name="1️⃣ Escolha o plano", value="Veja os planos em 💰planos-e-precos", inline=False)
        embed.add_field(name="2️⃣ Entre em contato", value="Abra um ticket em 📩abrir-ticket\nOu envie mensagem direta ao admin.", inline=False)
        embed.add_field(name="3️⃣ Efetue o pagamento", value="PIX, cartão de crédito ou boleto.", inline=False)
        embed.add_field(name="4️⃣ Receba sua chave", value="Sua chave de licença será enviada em até 5 minutos após confirmação.", inline=False)
        embed.add_field(name="5️⃣ Ative o GameBoost", value="Abra o programa e insira sua chave. Pronto! 🚀", inline=False)
        await ch.send(embed=embed)

    # ── MENSAGEM TICKET ──────────────────────────────────────
    ch = discord.utils.get(guild.text_channels, name="📩abrir-ticket")
    if ch:
        embed = discord.Embed(
            title="🎫 SUPORTE GAMEBOOST",
            description=(
                "Precisa de ajuda? Clique no botão abaixo para abrir um ticket.\n\n"
                "**Tipos de suporte:**\n"
                "🛒 Comprar licença\n"
                "🔑 Problema com ativação\n"
                "🐛 Bug ou erro no programa\n"
                "❓ Dúvida geral"
            ),
            color=COR_AZUL
        )
        view = TicketView()
        await ch.send(embed=embed, view=view)

    # Cargo ao dono
    await ctx.author.add_roles(cargo_map["👑 Dono"])
    await msg.edit(content="✅ **Servidor configurado com sucesso!**\nTodos os canais, cargos e mensagens foram criados.")

# ============================================================
#  SISTEMA DE TICKETS
# ============================================================
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🛒 Comprar Licença", style=discord.ButtonStyle.success, custom_id="ticket_comprar")
    async def ticket_comprar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await criar_ticket(interaction, "compra")

    @discord.ui.button(label="🔑 Ativar / Problema", style=discord.ButtonStyle.primary, custom_id="ticket_ativar")
    async def ticket_ativar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await criar_ticket(interaction, "ativacao")

    @discord.ui.button(label="🐛 Bug / Erro", style=discord.ButtonStyle.secondary, custom_id="ticket_bug")
    async def ticket_bug(self, interaction: discord.Interaction, button: discord.ui.Button):
        await criar_ticket(interaction, "bug")

    @discord.ui.button(label="❓ Dúvida Geral", style=discord.ButtonStyle.secondary, custom_id="ticket_duvida")
    async def ticket_duvida(self, interaction: discord.Interaction, button: discord.ui.Button):
        await criar_ticket(interaction, "duvida")

async def criar_ticket(interaction: discord.Interaction, tipo: str):
    guild = interaction.guild
    autor = interaction.user

    # Verifica se já tem ticket aberto
    ticket_nome = f"ticket-{autor.name.lower().replace(' ','-')}"
    existing = discord.utils.get(guild.text_channels, name=ticket_nome)
    if existing:
        return await interaction.response.send_message(
            f"Você já tem um ticket aberto: {existing.mention}", ephemeral=True
        )

    # Cria categoria de tickets se não existir
    cat = discord.utils.get(guild.categories, name="🎫 TICKETS ABERTOS")
    if not cat:
        cat = await guild.create_category("🎫 TICKETS ABERTOS")

    # Permissões do ticket - só o usuario e admins veem
    admin_role = discord.utils.get(guild.roles, name="🛡️ Admin")
    dono_role  = discord.utils.get(guild.roles, name="👑 Dono")
    suporte_role = discord.utils.get(guild.roles, name="⚡ Suporte")

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        autor: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True),
    }
    for r in [admin_role, dono_role, suporte_role]:
        if r:
            overwrites[r] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

    canal = await guild.create_text_channel(ticket_nome, category=cat, overwrites=overwrites)

    tipos_info = {
        "compra"   : ("🛒 COMPRA DE LICENÇA",    "Olá! Para comprar, informe qual plano deseja (Mensal ou Vitalício)."),
        "ativacao" : ("🔑 PROBLEMA DE ATIVAÇÃO",  "Olá! Informe sua chave de licença e descreva o problema."),
        "bug"      : ("🐛 REPORTE DE BUG",        "Olá! Descreva o erro que está ocorrendo e envie um print se possível."),
        "duvida"   : ("❓ DÚVIDA GERAL",          "Olá! Como podemos ajudá-lo hoje?"),
    }

    titulo, instrucao = tipos_info.get(tipo, ("🎫 TICKET", "Como posso ajudar?"))

    embed = discord.Embed(
        title=titulo,
        description=(
            f"Ticket aberto por {autor.mention}\n\n"
            f"**{instrucao}**\n\n"
            f"Nossa equipe responderá em breve.\n"
            f"Horário de atendimento: todos os dias"
        ),
        color=COR_AZUL,
        timestamp=datetime.now()
    )
    embed.set_footer(text=f"Ticket de {autor.name}")

    view = FecharTicketView()
    await canal.send(f"{autor.mention}", embed=embed, view=view)

    # Log no canal admin
    log_ch = discord.utils.get(guild.text_channels, name="📊logs-tickets")
    if log_ch:
        log_embed = discord.Embed(
            title="🎫 Novo Ticket",
            description=f"**Usuario:** {autor.mention}\n**Tipo:** {titulo}\n**Canal:** {canal.mention}",
            color=COR_LARANJA,
            timestamp=datetime.now()
        )
        await log_ch.send(embed=log_embed)

    await interaction.response.send_message(
        f"✅ Ticket criado: {canal.mention}", ephemeral=True
    )

class FecharTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Fechar Ticket", style=discord.ButtonStyle.danger, custom_id="fechar_ticket")
    async def fechar(self, interaction: discord.Interaction, button: discord.ui.Button):
        admin_role  = discord.utils.get(interaction.guild.roles, name="🛡️ Admin")
        dono_role   = discord.utils.get(interaction.guild.roles, name="👑 Dono")
        suporte_role= discord.utils.get(interaction.guild.roles, name="⚡ Suporte")
        is_staff = any(r in interaction.user.roles for r in [admin_role, dono_role, suporte_role] if r)

        if not is_staff and interaction.channel.name != f"ticket-{interaction.user.name.lower().replace(' ','-')}":
            return await interaction.response.send_message("Sem permissão para fechar este ticket.", ephemeral=True)

        embed = discord.Embed(
            title="🔒 Ticket Encerrado",
            description=f"Ticket fechado por {interaction.user.mention}",
            color=COR_VERMELHO,
            timestamp=datetime.now()
        )
        await interaction.channel.send(embed=embed)
        await asyncio.sleep(5)
        await interaction.channel.delete()
        await interaction.response.send_message("Ticket fechado.", ephemeral=True)

# ============================================================
#  COMANDOS SLASH
# ============================================================
@tree.command(name="licenca", description="Verifica uma licenca GameBoost")
@app_commands.describe(chave="Chave de licenca (XXXXX-XXXXX-XXXXX-XXXXX)")
async def verificar_licenca(interaction: discord.Interaction, chave: str):
    await interaction.response.defer(ephemeral=True)
    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{SHEETS_URL}?action=validate&key={chave}", allow_redirects=True, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                data = await resp.json(content_type=None)
        if data.get("valid"):
            embed = discord.Embed(title="✅ Licença Válida", color=COR_VERDE)
            embed.add_field(name="Cliente",    value=data.get("cliente","N/D"),   inline=True)
            embed.add_field(name="Expiracao",  value=data.get("expiracao","N/D"), inline=True)
            embed.add_field(name="Usos",       value=str(data.get("usos","N/D")), inline=True)
            await interaction.followup.send(embed=embed, ephemeral=True)

            # Da cargo de cliente
            cargo = discord.utils.get(interaction.guild.roles, name="✅ Cliente")
            if cargo:
                await interaction.user.add_roles(cargo)
        else:
            embed = discord.Embed(title="❌ Licença Inválida", description=data.get("msg","Chave inválida"), color=COR_VERMELHO)
            await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Erro ao verificar: {e}", ephemeral=True)

@tree.command(name="gerar", description="[ADMIN] Gera uma nova licenca")
@app_commands.describe(cliente="Nome do cliente", plano="mensal ou vitalicio")
async def gerar_licenca(interaction: discord.Interaction, cliente: str, plano: str):
    if interaction.user.id != ADMIN_ID:
        return await interaction.response.send_message("Sem permissao.", ephemeral=True)
    import random, string
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    chave = "-".join("".join(random.choices(chars, k=5)) for _ in range(4))
    dias  = 30 if plano.lower() == "mensal" else 0
    embed = discord.Embed(title="🔑 Licença Gerada", color=COR_LARANJA)
    embed.add_field(name="Cliente", value=cliente,                inline=True)
    embed.add_field(name="Plano",   value=plano.capitalize(),     inline=True)
    embed.add_field(name="Dias",    value="Vitalicio" if dias==0 else str(dias), inline=True)
    embed.add_field(name="Chave",   value=f"`{chave}`",           inline=False)
    embed.add_field(name="⚠️ Acao", value="Adicione esta chave na planilha Google Sheets!", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="ping", description="Verifica se o bot esta online")
async def ping(interaction: discord.Interaction):
    latencia = round(bot.latency * 1000)
    embed = discord.Embed(title="⚡ GAMEBOOST BOT", description=f"Online! Latencia: **{latencia}ms**", color=COR_VERDE)
    await interaction.response.send_message(embed=embed)

@tree.command(name="cargo", description="[ADMIN] Da cargo de premium para usuario")
@app_commands.describe(usuario="Usuario", tipo="mensal ou vitalicio")
async def dar_cargo(interaction: discord.Interaction, usuario: discord.Member, tipo: str):
    if interaction.user.id != ADMIN_ID:
        return await interaction.response.send_message("Sem permissao.", ephemeral=True)
    nome_cargo = "💎 PREMIUM Vitalicio" if "vit" in tipo.lower() else "🥇 PREMIUM Mensal"
    cargo = discord.utils.get(interaction.guild.roles, name=nome_cargo)
    cliente_cargo = discord.utils.get(interaction.guild.roles, name="✅ Cliente")
    if cargo:
        await usuario.add_roles(cargo)
    if cliente_cargo:
        await usuario.add_roles(cliente_cargo)
    embed = discord.Embed(title="✅ Cargo Atribuido", description=f"{usuario.mention} recebeu **{nome_cargo}**", color=COR_VERDE)
    await interaction.response.send_message(embed=embed)

# ============================================================
#  EVENTOS
# ============================================================
# ============================================================
#  COMANDO: GERAR LICENCA AUTOMATICAMENTE
# ============================================================
@tree.command(name="vender", description="[ADMIN] Gera e envia licenca para o cliente automaticamente")
@app_commands.describe(
    usuario="Usuario do Discord que comprou",
    plano="mensal, trimestral ou vitalicio",
    observacao="Observacao opcional (ex: pago via PIX)"
)
async def vender_licenca(interaction: discord.Interaction, usuario: discord.Member, plano: str, observacao: str = ""):
    if interaction.user.id != ADMIN_ID:
        return await interaction.response.send_message("Sem permissao.", ephemeral=True)

    plano = plano.lower()
    if plano not in PLANOS:
        return await interaction.response.send_message(
            f"Plano invalido! Use: {', '.join(PLANOS.keys())}", ephemeral=True
        )

    await interaction.response.defer(ephemeral=True)

    # Gera a chave
    chave = gerar_chave()
    info  = PLANOS[plano]

    # Registra no Google Sheets
    sucesso = await registrar_licenca_sheets(usuario.name, plano, chave)

    # Monta embed da chave
    embed_chave = discord.Embed(
        title="🎮 SUA LICENÇA GAMEBOOST PREMIUM",
        description=f"Olá {usuario.mention}! Sua licença foi gerada com sucesso!",
        color=0xFF6D00
    )
    embed_chave.add_field(name="📦 Plano",     value=info["nome"],  inline=True)
    embed_chave.add_field(name="💰 Valor",     value=info["preco"], inline=True)
    embed_chave.add_field(name="⏰ Validade",  value="Vitalício" if info["dias"]==0 else f"{info['dias']} dias", inline=True)
    embed_chave.add_field(
        name="🔑 Sua Chave de Licença",
        value=f"```{chave}```",
        inline=False
    )
    embed_chave.add_field(
        name="📥 Como ativar",
        value="1. Abra o **GameBoost Premium**\n2. Digite sua chave na tela de login\n3. Clique **ATIVAR LICENCA**\n4. Pronto!",
        inline=False
    )
    embed_chave.add_field(
        name="⚠️ Importante",
        value="• Esta licença é vinculada ao seu PC\n• Não compartilhe sua chave\n• Suporte: abra um ticket no servidor",
        inline=False
    )
    embed_chave.set_footer(text=f"GameBoost Premium • Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    # Envia por DM para o cliente
    try:
        await usuario.send(embed=embed_chave)
        dm_status = "✅ Chave enviada por DM"
    except:
        dm_status = "⚠️ Nao foi possivel enviar DM - envie manualmente"

    # Da cargo premium
    nome_cargo = "💎 PREMIUM Vitalicio" if plano == "vitalicio" else "🥇 PREMIUM Mensal"
    cargo = discord.utils.get(interaction.guild.roles, name=nome_cargo)
    cliente_cargo = discord.utils.get(interaction.guild.roles, name="✅ Cliente")
    if cargo:
        await usuario.add_roles(cargo)
    if cliente_cargo:
        await usuario.add_roles(cliente_cargo)

    # Log no canal admin
    log_ch = discord.utils.get(interaction.guild.text_channels, name="📈vendas")
    if log_ch:
        log_embed = discord.Embed(title="💰 Nova Venda!", color=0x00E676)
        log_embed.add_field(name="Cliente",  value=usuario.mention, inline=True)
        log_embed.add_field(name="Plano",    value=info["nome"],    inline=True)
        log_embed.add_field(name="Valor",    value=info["preco"],   inline=True)
        log_embed.add_field(name="Chave",    value=f"`{chave}`",    inline=False)
        log_embed.add_field(name="DM",       value=dm_status,       inline=False)
        log_embed.add_field(name="Sheets",   value="✅ Registrado" if sucesso else "⚠️ Erro - adicione manual", inline=False)
        if observacao:
            log_embed.add_field(name="Obs",  value=observacao,      inline=False)
        log_embed.set_footer(text=f"Vendido por {interaction.user.name}")
        await log_ch.send(embed=log_embed)

    # Resposta ao admin
    admin_embed = discord.Embed(title="✅ Venda Processada!", color=0x00E676)
    admin_embed.add_field(name="Cliente", value=usuario.mention, inline=True)
    admin_embed.add_field(name="Plano",   value=info["nome"],    inline=True)
    admin_embed.add_field(name="Chave",   value=f"`{chave}`",    inline=False)
    admin_embed.add_field(name="DM",      value=dm_status,       inline=False)
    admin_embed.add_field(name="Sheets",  value="✅ Registrado" if sucesso else "⚠️ Adicione manualmente na planilha", inline=False)
    await interaction.followup.send(embed=admin_embed, ephemeral=True)


@tree.command(name="resetar_hwid", description="[ADMIN] Reseta o HWID de uma licenca (cliente trocou de PC)")
@app_commands.describe(chave="Chave de licenca para resetar HWID")
async def resetar_hwid(interaction: discord.Interaction, chave: str):
    if interaction.user.id != ADMIN_ID:
        return await interaction.response.send_message("Sem permissao.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    try:
        url = f"{SHEETS_URL}?action=resetHWID&key={chave}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                result = await resp.json(content_type=None)
        if result.get("success"):
            await interaction.followup.send(f"HWID resetado para `{chave}`! O cliente pode ativar em um novo PC.", ephemeral=True)
        else:
            await interaction.followup.send(f"⚠️ {result.get('msg','Erro ao resetar')}", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Erro: {e}", ephemeral=True)


@tree.command(name="listar_vendas", description="[ADMIN] Lista as ultimas vendas")
async def listar_vendas(interaction: discord.Interaction):
    if interaction.user.id != ADMIN_ID:
        return await interaction.response.send_message("Sem permissao.", ephemeral=True)
    ch = discord.utils.get(interaction.guild.text_channels, name="📈vendas")
    if ch:
        await interaction.response.send_message(f"Veja o historico em {ch.mention}", ephemeral=True)
    else:
        await interaction.response.send_message("Canal de vendas nao encontrado.", ephemeral=True)


@tree.command(name="ativar", description="Ativa sua licenca GameBoost e recebe o cargo Premium")
@app_commands.describe(chave="Sua chave de licenca (XXXXX-XXXXX-XXXXX-XXXXX)")
async def ativar_licenca(interaction: discord.Interaction, chave: str):
    await interaction.response.defer(ephemeral=True)
    result = await validar_licenca_api(chave)
    if result.get("valid"):
        embed = discord.Embed(title="✅ Licença Ativada!", color=0x00E676)
        embed.add_field(name="Cliente",   value=result.get("cliente",""),   inline=True)
        embed.add_field(name="Expiracao", value=result.get("expiracao",""), inline=True)
        # Da cargo
        plano = result.get("expiracao","")
        nome_cargo = "💎 PREMIUM Vitalicio" if plano == "Vitalicio" else "🥇 PREMIUM Mensal"
        cargo = discord.utils.get(interaction.guild.roles, name=nome_cargo)
        cliente_cargo = discord.utils.get(interaction.guild.roles, name="✅ Cliente")
        if cargo: await interaction.user.add_roles(cargo)
        if cliente_cargo: await interaction.user.add_roles(cliente_cargo)
        embed.add_field(name="Cargo", value=f"✅ {nome_cargo} atribuido!", inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        embed = discord.Embed(title="❌ Licença Inválida", description=result.get("msg","Chave invalida"), color=0xFF3C50)
        await interaction.followup.send(embed=embed, ephemeral=True)


# ============================================================
#  PAINEL ADMIN - GERADOR MANUAL DE LICENCAS
# ============================================================

# Estado temporario das configuracoes do painel
painel_estado = {}

class PainelTipoView(discord.ui.View):
    """Primeiro passo: escolher tipo de validade"""
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.select(
        placeholder="📅 Tipo de validade...",
        custom_id="select_tipo",
        options=[
            discord.SelectOption(label="Vitalicio",      value="vitalicio",   emoji="💎", description="Sem data de expiracao"),
            discord.SelectOption(label="Por dias",        value="dias",        emoji="📅", description="Expira apos X dias"),
            discord.SelectOption(label="Por usos",        value="usos",        emoji="🔢", description="Expira apos X ativacoes"),
            discord.SelectOption(label="Mensal (30d)",    value="mensal",      emoji="🥇", description="30 dias automatico"),
            discord.SelectOption(label="Trimestral (90d)",value="trimestral",  emoji="🏆", description="90 dias automatico"),
            discord.SelectOption(label="Semestral (180d)",value="semestral",   emoji="🌟", description="180 dias automatico"),
        ]
    )
    async def select_tipo(self, interaction: discord.Interaction, select: discord.ui.Select):
        if interaction.user.id != ADMIN_ID:
            return await interaction.response.send_message("Sem permissao.", ephemeral=True)

        tipo = select.values[0]
        uid  = str(interaction.user.id)
        painel_estado[uid] = {"tipo": tipo}

        if tipo == "vitalicio":
            painel_estado[uid]["dias"] = 0
            painel_estado[uid]["usos"] = 999
            await interaction.response.edit_message(
                embed=build_painel_embed(uid),
                view=PainelClienteView()
            )
        elif tipo in ["mensal","trimestral","semestral"]:
            dias_map = {"mensal":30,"trimestral":90,"semestral":180}
            painel_estado[uid]["dias"] = dias_map[tipo]
            painel_estado[uid]["usos"] = 999
            await interaction.response.edit_message(
                embed=build_painel_embed(uid),
                view=PainelClienteView()
            )
        elif tipo == "dias":
            await interaction.response.edit_message(
                embed=build_painel_embed(uid, status="Quantos dias de validade?"),
                view=PainelDiasView()
            )
        elif tipo == "usos":
            await interaction.response.edit_message(
                embed=build_painel_embed(uid, status="Quantos usos permitidos?"),
                view=PainelUsosView()
            )

class PainelDiasView(discord.ui.View):
    """Selecionar numero de dias"""
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.select(
        placeholder="📅 Quantidade de dias...",
        custom_id="select_dias",
        options=[
            discord.SelectOption(label="7 dias",    value="7",   emoji="📅"),
            discord.SelectOption(label="15 dias",   value="15",  emoji="📅"),
            discord.SelectOption(label="30 dias",   value="30",  emoji="📅"),
            discord.SelectOption(label="60 dias",   value="60",  emoji="📅"),
            discord.SelectOption(label="90 dias",   value="90",  emoji="📅"),
            discord.SelectOption(label="180 dias",  value="180", emoji="📅"),
            discord.SelectOption(label="365 dias",  value="365", emoji="📅"),
        ]
    )
    async def select_dias(self, interaction: discord.Interaction, select: discord.ui.Select):
        uid = str(interaction.user.id)
        painel_estado[uid]["dias"] = int(select.values[0])
        painel_estado[uid]["usos"] = 999
        await interaction.response.edit_message(
            embed=build_painel_embed(uid),
            view=PainelClienteView()
        )

    @discord.ui.button(label="← Voltar", style=discord.ButtonStyle.secondary, custom_id="back_dias")
    async def voltar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            embed=build_painel_embed_inicial(),
            view=PainelTipoView()
        )

class PainelUsosView(discord.ui.View):
    """Selecionar numero de usos"""
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.select(
        placeholder="🔢 Quantidade de usos...",
        custom_id="select_usos",
        options=[
            discord.SelectOption(label="1 uso",   value="1",   emoji="1️⃣", description="Ativa em 1 PC"),
            discord.SelectOption(label="2 usos",  value="2",   emoji="2️⃣", description="Ativa em 2 PCs"),
            discord.SelectOption(label="3 usos",  value="3",   emoji="3️⃣", description="Ativa em 3 PCs"),
            discord.SelectOption(label="5 usos",  value="5",   emoji="5️⃣", description="Ativa em 5 PCs"),
            discord.SelectOption(label="10 usos", value="10",  emoji="🔟", description="Ativa em 10 PCs"),
        ]
    )
    async def select_usos(self, interaction: discord.Interaction, select: discord.ui.Select):
        uid = str(interaction.user.id)
        painel_estado[uid]["usos"] = int(select.values[0])
        painel_estado[uid]["dias"] = 0
        await interaction.response.edit_message(
            embed=build_painel_embed(uid),
            view=PainelClienteView()
        )

    @discord.ui.button(label="← Voltar", style=discord.ButtonStyle.secondary, custom_id="back_usos")
    async def voltar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            embed=build_painel_embed_inicial(),
            view=PainelTipoView()
        )

class PainelClienteView(discord.ui.View):
    """Terceiro passo: definir nome e gerar"""
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="✏️ Definir Nome do Cliente", style=discord.ButtonStyle.primary, custom_id="set_nome")
    async def set_nome(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != ADMIN_ID:
            return await interaction.response.send_message("Sem permissao.", ephemeral=True)
        await interaction.response.send_modal(NomeClienteModal())

    @discord.ui.button(label="⚡ Gerar Chave AGORA", style=discord.ButtonStyle.success, custom_id="gerar_agora", emoji="🔑")
    async def gerar_agora(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != ADMIN_ID:
            return await interaction.response.send_message("Sem permissao.", ephemeral=True)

        uid = str(interaction.user.id)
        estado = painel_estado.get(uid, {})
        cliente = estado.get("nome", "Cliente")
        tipo    = estado.get("tipo", "vitalicio")
        dias    = estado.get("dias", 0)
        usos    = estado.get("usos", 999)

        chave = gerar_chave()
        sucesso = await registrar_licenca_sheets(cliente, tipo, chave)

        embed = discord.Embed(title="🔑 CHAVE GERADA!", color=0xFF6D00)
        embed.add_field(name="👤 Cliente",  value=cliente,                    inline=True)
        embed.add_field(name="📦 Tipo",     value=tipo.capitalize(),          inline=True)
        embed.add_field(name="⏰ Validade", value="Vitalicio" if dias==0 else f"{dias} dias", inline=True)
        embed.add_field(name="🔢 Usos",     value=str(usos),                  inline=True)
        embed.add_field(name="📊 Planilha", value="✅ Registrado" if sucesso else "⚠️ Adicione manual", inline=True)
        embed.add_field(name="🔑 CHAVE",    value=f"```{chave}```",           inline=False)
        embed.set_footer(text=f"Gerado por {interaction.user.name} • {datetime.now().strftime('%d/%m/%Y %H:%M')}")

        await interaction.response.edit_message(embed=embed, view=PainelAposGerarView(chave, cliente))

        # Log no canal vendas
        log_ch = discord.utils.get(interaction.guild.text_channels, name="📈vendas")
        if log_ch:
            await log_ch.send(embed=embed)

    @discord.ui.button(label="← Voltar", style=discord.ButtonStyle.secondary, custom_id="back_cliente")
    async def voltar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            embed=build_painel_embed_inicial(),
            view=PainelTipoView()
        )

class PainelAposGerarView(discord.ui.View):
    """View apos gerar a chave"""
    def __init__(self, chave: str, cliente: str):
        super().__init__(timeout=300)
        self.chave   = chave
        self.cliente = cliente

    @discord.ui.button(label="📋 Copiar Chave", style=discord.ButtonStyle.secondary, custom_id="copiar")
    async def copiar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"`{self.chave}`", ephemeral=True)

    @discord.ui.button(label="📨 Enviar para Usuario", style=discord.ButtonStyle.primary, custom_id="enviar_user")
    async def enviar_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EnviarChaveModal(self.chave))

    @discord.ui.button(label="🔄 Nova Chave", style=discord.ButtonStyle.success, custom_id="nova_chave")
    async def nova_chave(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            embed=build_painel_embed_inicial(),
            view=PainelTipoView()
        )

class NomeClienteModal(discord.ui.Modal, title="Nome do Cliente"):
    nome = discord.ui.TextInput(
        label="Nome do cliente",
        placeholder="Ex: João Silva",
        max_length=50,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        if uid not in painel_estado:
            painel_estado[uid] = {}
        painel_estado[uid]["nome"] = self.nome.value
        await interaction.response.edit_message(
            embed=build_painel_embed(uid),
            view=PainelClienteView()
        )

class EnviarChaveModal(discord.ui.Modal, title="Enviar Chave para Usuario"):
    def __init__(self, chave: str):
        super().__init__()
        self.chave = chave

    user_id = discord.ui.TextInput(
        label="ID do usuario no Discord",
        placeholder="Ex: 279638596195975178",
        max_length=20,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            user = await interaction.client.fetch_user(int(self.user_id.value))
            embed = discord.Embed(
                title="🎮 SUA LICENÇA GAMEBOOST PREMIUM",
                description="Sua licença foi gerada! Siga os passos abaixo para ativar.",
                color=0xFF6D00
            )
            embed.add_field(name="🔑 Chave", value=f"```{self.chave}```", inline=False)
            embed.add_field(
                name="📥 Como ativar",
                value="1. Abra o **GameBoost Premium**\n2. Digite sua chave\n3. Clique **ATIVAR LICENCA**\n4. Pronto!",
                inline=False
            )
            if os.path.exists(EXE_PATH):
                exe_file = discord.File(EXE_PATH, filename="GameBoost_Premium.exe")
                await user.send(embed=embed, file=exe_file)
            else:
                await user.send(embed=embed)
            await interaction.response.send_message(f"✅ Chave e arquivo enviados para {user.mention}!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {e}", ephemeral=True)

def build_painel_embed_inicial():
    embed = discord.Embed(
        title="🔑 PAINEL DE LICENÇAS — GameBoost Premium",
        description="Selecione o **tipo de validade** para gerar uma nova licença:",
        color=0xFF6D00
    )
    embed.add_field(name="💎 Vitalicio",       value="Sem expiracao",          inline=True)
    embed.add_field(name="📅 Por dias",         value="Ex: 30, 60, 90 dias",    inline=True)
    embed.add_field(name="🔢 Por usos",         value="Ex: 1, 2, 5 usos",       inline=True)
    embed.add_field(name="🥇 Mensal",           value="30 dias automatico",     inline=True)
    embed.add_field(name="🏆 Trimestral",       value="90 dias automatico",     inline=True)
    embed.add_field(name="🌟 Semestral",        value="180 dias automatico",    inline=True)
    embed.set_footer(text="GameBoost Premium • Painel Admin")
    return embed

def build_painel_embed(uid: str, status: str = ""):
    estado = painel_estado.get(uid, {})
    embed  = discord.Embed(title="🔑 PAINEL DE LICENÇAS — Configurando...", color=0xFF6D00)
    if estado.get("tipo"):
        embed.add_field(name="📦 Tipo",     value=estado["tipo"].capitalize(), inline=True)
    if estado.get("dias") is not None:
        val = "Vitalicio" if estado["dias"]==0 else f"{estado['dias']} dias"
        embed.add_field(name="⏰ Validade", value=val, inline=True)
    if estado.get("usos"):
        embed.add_field(name="🔢 Usos",    value=str(estado["usos"]), inline=True)
    if estado.get("nome"):
        embed.add_field(name="👤 Cliente", value=estado["nome"], inline=True)
    if status:
        embed.add_field(name="➡️ Proximo passo", value=status, inline=False)
    else:
        falta = []
        if not estado.get("nome"): falta.append("Nome do cliente")
        if falta:
            embed.add_field(name="➡️ Faltando", value="\n".join(f"• {f}" for f in falta), inline=False)
        else:
            embed.add_field(name="✅ Pronto!", value="Clique em **Gerar Chave AGORA**", inline=False)
    embed.set_footer(text="GameBoost Premium • Painel Admin")
    return embed


@tree.command(name="painel_licencas", description="[ADMIN] Abre o painel visual de geracao de licencas")
async def painel_licencas(interaction: discord.Interaction):
    if interaction.user.id != ADMIN_ID:
        return await interaction.response.send_message("Sem permissao.", ephemeral=True)
    await interaction.response.send_message(
        embed=build_painel_embed_inicial(),
        view=PainelTipoView(),
        ephemeral=True
    )


@tree.command(name="setup_painel", description="[ADMIN] Cria o canal do painel de licencas permanente")
async def setup_painel(interaction: discord.Interaction):
    if interaction.user.id != ADMIN_ID:
        return await interaction.response.send_message("Sem permissao.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)

    # Cria ou encontra canal
    admin_role = discord.utils.get(interaction.guild.roles, name="🛡️ Admin")
    dono_role  = discord.utils.get(interaction.guild.roles, name="👑 Dono")
    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
    }
    for r in [admin_role, dono_role]:
        if r: overwrites[r] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

    cat = discord.utils.get(interaction.guild.categories, name="🔧 ADMIN")
    ch  = discord.utils.get(interaction.guild.text_channels, name="🔑gerenciar-licencas")
    if not ch:
        ch = await interaction.guild.create_text_channel("🔑gerenciar-licencas", category=cat, overwrites=overwrites)

    embed = discord.Embed(
        title="🔑 PAINEL DE LICENÇAS GAMEBOOST",
        description=(
            "Use os comandos abaixo para gerenciar licencas:\n\n"
            "**`/painel_licencas`** - Abre painel visual completo\n"
            "**`/vender @user plano`** - Venda rapida com DM automatica\n"
            "**`/licenca CHAVE`** - Consultar licenca\n"
            "**`/resetar_hwid CHAVE`** - Resetar PC vinculado\n"
            "**`/cargo @user tipo`** - Dar cargo premium\n\n"
            "**Planos:** `mensal` | `trimestral` | `vitalicio`"
        ),
        color=0xFF6D00
    )
    embed.add_field(
        name="📊 Planilha Google Sheets",
        value="[Abrir Planilha](https://sheets.google.com) — Coluna G = HWID | Coluna H = Admin",
        inline=False
    )
    embed.set_footer(text="GameBoost Premium • Apenas admins visualizam este canal")
    await ch.send(embed=embed)
    await interaction.followup.send(f"✅ Painel configurado em {ch.mention}!", ephemeral=True)



@tree.command(name="setup_canais", description="[ADMIN] Preenche todos os canais do servidor com conteudo completo")
async def setup_canais(interaction: discord.Interaction):
    if interaction.user.id != ADMIN_ID:
        return await interaction.response.send_message("Sem permissao.", ephemeral=True)

    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    erros = []

    def get_ch(nome):
        for ch in guild.text_channels:
            if nome.lower() in ch.name.lower():
                return ch
        return None

    # ── BOAS VINDAS
    ch = get_ch("boas-vindas")
    if ch:
        await ch.purge(limit=10)
        e = discord.Embed(title="⚡ BEM-VINDO AO GAMEBOOST PREMIUM!", description="O **otimizador mais completo** para Windows — feito para quem leva games a sério.
O GameBoost aplica mais de **40 otimizações automáticas** no seu PC.", color=0xFF6D00)
        e.add_field(name="🚀 O que o GameBoost faz?", value="• Otimiza CPU, RAM e GPU automaticamente
• Desativa serviços desnecessários do Windows
• Aplica tweaks avançados de desempenho
• Libera memória RAM com 1 clique
• Configura RAM Virtual para PCs com pouca RAM
• Gera relatório completo do seu sistema", inline=False)
        e.add_field(name="📌 Por onde começar?", value="1️⃣ Leia as **#regras**
2️⃣ Veja os **#planos-e-precos**
3️⃣ Compre em **#comprar-licenca**
4️⃣ Baixe em **#download-gameboost**
5️⃣ Dúvidas? Abra um ticket em **#abrir-ticket**", inline=False)
        e.set_footer(text="GameBoost Premium • Criado por matraka")
        await ch.send(embed=e)
    else:
        erros.append("boas-vindas")

    # ── REGRAS
    ch = get_ch("regras")
    if ch:
        await ch.purge(limit=10)
        e = discord.Embed(title="📋 REGRAS DO SERVIDOR", description="Para manter o ambiente saudável e organizado, siga as regras abaixo:", color=0xFF6D00)
        e.add_field(name="1️⃣ Respeito acima de tudo", value="Trate todos com educação. Ofensas ou discriminação resultam em banimento imediato.", inline=False)
        e.add_field(name="2️⃣ Sem spam ou flood", value="Não envie mensagens repetidas, links desnecessários ou conteúdo fora do contexto.", inline=False)
        e.add_field(name="3️⃣ Sem pirataria ou cheats", value="É proibido compartilhar cheats, hacks ou software pirata. Resulta em ban permanente.", inline=False)
        e.add_field(name="4️⃣ Licenças são pessoais", value="Sua licença é vinculada ao seu PC (HWID). Não compartilhe, revenda ou transfira.", inline=False)
        e.add_field(name="5️⃣ Suporte pelo ticket", value="Não envie DM para admins. Use **#abrir-ticket** para suporte oficial.", inline=False)
        e.add_field(name="6️⃣ Canais com propósito", value="Use cada canal para o que foi criado. Mantenha conversas nos canais corretos.", inline=False)
        e.set_footer(text="O não cumprimento pode resultar em mute, kick ou ban.")
        await ch.send(embed=e)
    else:
        erros.append("regras")

    # ── NOVIDADES / TUTORIAL
    ch = get_ch("novidades")
    if ch:
        await ch.purge(limit=20)
        e0 = discord.Embed(title="🎮 GAMEBOOST PREMIUM — Guia Completo", description="Bem-vindo ao tutorial oficial! Aqui você aprende a usar cada aba para extrair o máximo do seu PC.", color=0xFF6D00)
        e0.set_footer(text="GameBoost Premium v1.0 • Criado por matraka")
        await ch.send(embed=e0)

        e1 = discord.Embed(title="⚡ ABA BOOST — Otimização Completa", description="A aba principal. Com **1 clique** aplica mais de 40 otimizações no seu PC.", color=0xFF6D00)
        e1.add_field(name="🔧 O que ela faz?", value="• **CPU** — Ativa todos os núcleos, desativa Core Parking, maximiza prioridade para games
• **RAM** — Desativa paginação executiva e SuperFetch
• **GPU** — Ativa HAGS, desativa MPO, tweaks NVIDIA/AMD automáticos
• **Limpeza** — Temporários, Prefetch, lixeira e DNS
• **Windows** — Desativa GameBar, telemetria, Cortana e 10 serviços pesados
• **Energia** — Ativa Ultimate Performance", inline=False)
        e1.add_field(name="▶️ Como usar", value="1. Execute como **Administrador**
2. Clique **INICIAR BOOST**
3. Aguarde concluir
4. **Reinicie o PC**", inline=False)
        e1.add_field(name="↩️ Restaurar", value="O botão **RESTAURAR** reverte tudo ao estado original antes do boost.", inline=False)
        e1.set_footer(text="Dica: sempre reinicie após o boost!")
        await ch.send(embed=e1)

        e2 = discord.Embed(title="📊 ABA RELATÓRIO — Monitor do Sistema", description="Veja CPU, RAM, disco e o resultado de cada módulo otimizado em tempo real.", color=0x00B4DC)
        e2.add_field(name="📈 Informações", value="• CPU, RAM, Disco, GPU e Uptime em tempo real
• Cards com resultado de cada módulo após o BOOST
• Botão **LIMPAR RAM** para liberar memória instantaneamente", inline=False)
        e2.set_footer(text="✅ Disponível na versão gratuita e premium")
        await ch.send(embed=e2)

        e3 = discord.Embed(title="🔧 ABA TWEAKS — Controle Total 🔒 PREMIUM", description="Aplique tweaks individuais com checkboxes — você escolhe exatamente o que ativar.", color=0xFF6D00)
        e3.add_field(name="⚙️ Categorias", value="Sistema • Windows Update • Privacidade • Jogos • GPU NVIDIA • GPU AMD • CPU/RAM • Limpeza", inline=False)
        e3.add_field(name="▶️ Como usar", value="Marque os tweaks desejados → **APLICAR TWEAKS** → Reinicie o PC", inline=False)
        await ch.send(embed=e3)

        e4 = discord.Embed(title="💾 ABA RAM VIRTUAL — Mais Memória 🔒 PREMIUM", description="Use o espaço do HD/SSD como memória extra. Ideal para PCs com **menos de 8GB de RAM**.", color=0x00B4DC)
        e4.add_field(name="🤔 Quando usar?", value="• Tem 8GB ou menos de RAM
• Jogos travando por falta de memória
• PC lento com vários programas abertos", inline=False)
        e4.add_field(name="▶️ Como usar", value="1. Abra a aba **RAM VIRTUAL**
2. Ajuste o slider ou use um preset
3. Clique **APLICAR**
4. **Reinicie o PC**", inline=False)
        e4.add_field(name="⚠️ Dica", value="SSD é muito melhor que HD para RAM Virtual. Quanto mais rápido o disco, melhor!", inline=False)
        await ch.send(embed=e4)

        e5 = discord.Embed(title="💡 DICA IMPORTANTE — Tem menos de 8GB de RAM?", description="Se tem **4GB ou 8GB de RAM**, ative a **RAM Virtual** ANTES do BOOST!

**Sequência recomendada:**
1. Aba RAM VIRTUAL → Aplicar → Reiniciar
2. Rodar o BOOST → Reiniciar

Isso garante o máximo desempenho! 🚀", color=0xFFB300)
        e5.set_footer(text="GameBoost Premium • Dica oficial")
        await ch.send(embed=e5)
    else:
        erros.append("novidades")

    # ── STATUS BOT
    ch = get_ch("status-do-bot")
    if ch:
        await ch.purge(limit=10)
        e = discord.Embed(title="📊 STATUS DO SISTEMA GAMEBOOST", color=0x00E676)
        e.add_field(name="🤖 Bot Discord",  value="🟢 Online",           inline=True)
        e.add_field(name="📊 Licenças",      value="🟢 Operacional",      inline=True)
        e.add_field(name="☁️ Servidor",      value="🟢 Railway — Online", inline=True)
        e.add_field(name="🔑 Ativações",     value="🟢 Funcionando",      inline=True)
        e.add_field(name="📥 Downloads",     value="🟢 Disponível",       inline=True)
        e.add_field(name="🎫 Tickets",       value="🟢 Abertos",          inline=True)
        e.set_footer(text="GameBoost Premium • Status em tempo real")
        await ch.send(embed=e)
    else:
        erros.append("status-do-bot")

    # ── PLANOS E PRECOS
    ch = get_ch("planos-e-precos")
    if ch:
        await ch.purge(limit=10)
        e = discord.Embed(title="💰 PLANOS GAMEBOOST PREMIUM", description="Escolha o plano ideal e comece a otimizar seu PC agora!", color=0xFF6D00)
        e.add_field(name="🥇 Mensal — R$ 19,90", value="✅ BOOST completo (40+ otimizações)
✅ Tweaks avançados
✅ RAM Virtual
✅ Suporte via ticket
⏰ Validade: 30 dias", inline=True)
        e.add_field(name="🏆 Trimestral — R$ 44,90", value="✅ Tudo do Mensal
✅ Economia de R$ 15,00
✅ Prioridade no suporte
✅ Acesso a updates
⏰ Validade: 90 dias", inline=True)
        e.add_field(name="💎 Vitalício — R$ 34,90", value="✅ Tudo incluso para sempre
✅ Sem mensalidade
✅ Todas as atualizações futuras
✅ Suporte vitalício
⏰ Validade: Para sempre 🔥", inline=True)
        e.add_field(name="🆓 Versão Gratuita", value="• Limpeza de RAM
• Relatório do sistema
❌ Sem BOOST completo
❌ Sem Tweaks
❌ Sem RAM Virtual", inline=False)
        e.set_footer(text="Para comprar vá em #comprar-licenca ou abra um ticket!")
        await ch.send(embed=e)
    else:
        erros.append("planos-e-precos")

    # ── COMPRAR LICENCA
    ch = get_ch("comprar-licenca")
    if ch:
        await ch.purge(limit=10)
        e = discord.Embed(title="🎟️ COMO COMPRAR SUA LICENÇA", description="Adquira sua licença GameBoost Premium em poucos passos!", color=0xFF6D00)
        e.add_field(name="📋 Passo a passo", value="1️⃣ Escolha seu plano em **#planos-e-precos**
2️⃣ Abra um ticket em **#abrir-ticket**
3️⃣ Informe o plano desejado
4️⃣ Realize o pagamento (PIX)
5️⃣ Receba sua chave por DM em instantes!
6️⃣ Ative e aproveite 🚀", inline=False)
        e.add_field(name="💳 Pagamento", value="• PIX
• PicPay
• Outros — consulte no ticket", inline=True)
        e.add_field(name="⚡ Entrega", value="Imediato após confirmação!", inline=True)
        e.set_footer(text="Dúvidas? Abra um ticket!")
        await ch.send(embed=e)
    else:
        erros.append("comprar-licenca")

    # ── COMO ATIVAR
    ch = get_ch("como-ativar")
    if ch:
        await ch.purge(limit=10)
        e = discord.Embed(title="✅ COMO ATIVAR SUA LICENÇA", description="Após receber sua chave por DM, siga os passos:", color=0x00E676)
        e.add_field(name="📥 1. Baixe o GameBoost", value="Acesse **#download-gameboost** e baixe o `GameBoost_Premium.exe`", inline=False)
        e.add_field(name="🖱️ 2. Execute como Administrador", value="Botão direito → **Executar como administrador** ⚠️ Obrigatório!", inline=False)
        e.add_field(name="🔑 3. Digite sua chave", value="Cole sua chave no formato:
```XXXXX-XXXXX-XXXXX-XXXXX```", inline=False)
        e.add_field(name="✅ 4. Clique ATIVAR LICENÇA", value="O programa verifica e libera todas as funções premium!", inline=False)
        e.add_field(name="⚡ 5. Rode o BOOST", value="Clique **INICIAR BOOST**, aguarde e reinicie o PC.", inline=False)
        e.add_field(name="❓ Problemas?", value="Abra um ticket em **#abrir-ticket**!", inline=False)
        e.set_footer(text="GameBoost Premium • Suporte via ticket")
        await ch.send(embed=e)
    else:
        erros.append("como-ativar")

    # ── MINHAS LICENCAS
    ch = get_ch("minhas-licencas")
    if ch:
        await ch.purge(limit=10)
        e = discord.Embed(title="🔑 GERENCIAR SUA LICENÇA", description="Tudo sobre sua licença em um lugar só.", color=0xFF6D00)
        e.add_field(name="🔍 Verificar chave", value="Use `/licenca SUACHAVE` para ver status, expiração e PC vinculado.", inline=False)
        e.add_field(name="💻 Trocou de PC?", value="Abra um ticket e peça o reset de HWID. Gratuito para clientes ativos!", inline=False)
        e.add_field(name="🔄 Renovar", value="Para renovar ou fazer upgrade, abra um ticket em **#abrir-ticket**.", inline=False)
        e.add_field(name="⚠️ Licença expirada?", value="O programa abre em modo gratuito. Renove para reativar o premium!", inline=False)
        e.set_footer(text="Sua licença é pessoal e intransferível")
        await ch.send(embed=e)
    else:
        erros.append("minhas-licencas")

    # ── DICAS EXCLUSIVAS
    ch = get_ch("dicas-exclusivas")
    if ch:
        await ch.purge(limit=20)
        msgs = [
            discord.Embed(title="💡 DICAS EXCLUSIVAS PREMIUM", description="Dicas para extrair o máximo do seu PC!", color=0xFF6D00),
        ]
        d1 = discord.Embed(title="🖥️ DICA 1 — Modo de Energia", color=0xFF6D00)
        d1.add_field(name="Ultimate Performance", value="O GameBoost já ativa automaticamente. Confirme em:
`Painel de Controle → Opções de Energia`
Se não aparecer, rode o BOOST novamente.", inline=False)
        d2 = discord.Embed(title="🎮 DICA 2 — Configurações no Jogo", color=0xFF6D00)
        d2.add_field(name="Para melhor FPS", value="• Desative **V-Sync**
• Use **Fullscreen** (não janela)
• Desative **Motion Blur**
• Sombras no **mínimo**
• Ative modo alta performance no painel NVIDIA/AMD", inline=False)
        d3 = discord.Embed(title="💾 DICA 3 — RAM Virtual", color=0x00B4DC)
        d3.add_field(name="Configuração recomendada", value="• 4GB RAM → Use **8GB** de RAM Virtual
• 8GB RAM → Use **8-16GB** de RAM Virtual
• 16GB+ RAM → Não é necessário

Sempre use **SSD** se possível!", inline=False)
        d4 = discord.Embed(title="🔄 DICA 4 — Frequência do BOOST", color=0xFF6D00)
        d4.add_field(name="Com que frequência?", value="• **Após instalar Windows** → Rode uma vez
• **Após updates grandes** → Rode novamente
• **Uso diário** → Use só o **LIMPAR RAM**
• **Tweaks** → Configure uma vez e esqueça", inline=False)
        d5 = discord.Embed(title="🌡️ DICA 5 — Temperatura", color=0xFFB300)
        d5.add_field(name="Fique de olho!", value="• **CPU** → Ideal abaixo de 80°C em carga
• **GPU** → Ideal abaixo de 85°C em carga

Se esquentar demais, use **RESTAURAR** para encontrar a configuração ideal.", inline=False)
        for emb in [msgs[0], d1, d2, d3, d4, d5]:
            await ch.send(embed=emb)
    else:
        erros.append("dicas-exclusivas")

    # ── ABRIR TICKET
    ch = get_ch("abrir-ticket")
    if ch:
        await ch.purge(limit=10)
        e = discord.Embed(title="🎫 SUPORTE GAMEBOOST PREMIUM", description="Precisa de ajuda? Nossa equipe está pronta para atender!", color=0xFF6D00)
        e.add_field(name="📋 Tipos de suporte", value="🛒 Comprar licença
🔑 Ativar licença
💻 Trocar PC (reset HWID)
🔄 Renovar ou upgrade
🐛 Bug no programa
❓ Qualquer dúvida", inline=False)
        e.add_field(name="⏰ Atendimento", value="Segunda a Domingo — o mais rápido possível!", inline=True)
        e.add_field(name="⚠️ Importante", value="Não envie DM para admins. Use sempre este canal!", inline=True)
        e.set_footer(text="GameBoost Premium • Suporte oficial")
        await ch.send(embed=e)
    else:
        erros.append("abrir-ticket")

    # ── RESULTADO
    if erros:
        await interaction.followup.send(f"✅ Canais preenchidos!\n⚠️ Não encontrados: {', '.join(erros)}", ephemeral=True)
    else:
        await interaction.followup.send("✅ Todos os canais foram preenchidos com sucesso!", ephemeral=True)


@tree.command(name="setup_download", description="[ADMIN] Posta o GameBoost no canal de download")
async def setup_download(interaction: discord.Interaction):
    if interaction.user.id != ADMIN_ID:
        return await interaction.response.send_message("Sem permissao.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    ch = discord.utils.get(interaction.guild.text_channels, name="🚀download-gameboost")
    if not ch:
        for c in interaction.guild.text_channels:
            if "download" in c.name.lower():
                ch = c
                break
    if not ch:
        return await interaction.followup.send("❌ Canal download nao encontrado.", ephemeral=True)
    embed = discord.Embed(title="⚡ GAMEBOOST PREMIUM — Download Oficial", description="Baixe o **GameBoost Premium** clicando no arquivo abaixo.\n\n**Como ativar:**\n1. Baixe e execute o arquivo\n2. Digite sua **chave de licenca**\n3. Clique **ATIVAR LICENCA**\n4. Pronto! 🚀\n\n**Nao tem licenca?** Adquira em **#comprar-licenca** ou abra um ticket.", color=0xFF6D00)
    embed.add_field(name="✅ Versao",   value="v1.0 — Estavel",          inline=True)
    embed.add_field(name="💻 Sistema",  value="Windows 10/11",            inline=True)
    embed.add_field(name="🔒 Seguro",   value="Sem virus — 100% limpo",   inline=True)
    embed.set_footer(text="GameBoost Premium • Criado por matraka")
    if os.path.exists(EXE_PATH):
        exe_file = discord.File(EXE_PATH, filename="GameBoost_Premium.exe")
        await ch.send(embed=embed, file=exe_file)
        await interaction.followup.send(f"✅ Download postado em {ch.mention}!", ephemeral=True)
    else:
        await ch.send(embed=embed)
        await interaction.followup.send("⚠️ Embed postado mas exe nao encontrado. Adicione GameBoost_Premium.exe no repo.", ephemeral=True)


@bot.event
async def on_ready():
    # Sync global
    await tree.sync()
    # Sync por servidor para atualizacao instantanea
    for guild in bot.guilds:
        try:
            tree.copy_global_to(guild=guild)
            await tree.sync(guild=guild)
            print(f"Comandos sincronizados: {guild.name}")
        except Exception as e:
            print(f"Erro sync {guild.name}: {e}")
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name="⚡ GameBoost Premium"),
        status=discord.Status.online
    )
    print(f"Bot online: {bot.user}")
    print(f"Servidores: {len(bot.guilds)}")

@bot.event
async def on_member_join(member: discord.Member):
    # Da cargo de visitante automaticamente
    cargo = discord.utils.get(member.guild.roles, name="👤 Visitante")
    if cargo:
        await member.add_roles(cargo)

    # Mensagem de boas vindas
    ch = discord.utils.get(member.guild.text_channels, name="📌boas-vindas")
    if ch:
        embed = discord.Embed(
            title=f"⚡ Bem-vindo, {member.name}!",
            description=(
                f"Olá {member.mention}, bem-vindo ao **GameBoost Premium**!\n\n"
                "📋 Leia as regras em 📋regras\n"
                "💰 Veja os planos em 💰planos-e-precos\n"
                "🎟️ Compre em 🎟️comprar-licenca\n"
                "❓ Dúvidas? Abra um ticket em 📩abrir-ticket"
            ),
            color=COR_LARANJA
        )
        await ch.send(embed=embed)

# ============================================================
#  INICIAR BOT
# ============================================================
bot.run(TOKEN)
