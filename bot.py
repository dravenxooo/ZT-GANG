"""
ZT - Zéro Tolérance | Bot Discord
═══════════════════════════════════════════════════
  Bot officiel du gang ZT - Esthétique sombre & pro
═══════════════════════════════════════════════════
"""
import os
import asyncio
import logging
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("zt-bot")

# ═══════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════
TOKEN = os.environ.get("DISCORD_TOKEN")
GUILD_ID = os.environ.get("GUILD_ID")
GANG_NAME = os.environ.get("GANG_NAME", "ZT — Zéro Tolérance")

# Palette ZT (sombre/luxe)
COLOR_MAIN = 0x1A1A1A      # Noir charbon
COLOR_ACCENT = 0x8B0000    # Rouge sang
COLOR_SUCCESS = 0x1F4E1F   # Vert forêt sombre
COLOR_DANGER = 0x4A0E0E    # Crimson sombre
COLOR_WARN = 0x8B6914      # Or vieilli
COLOR_INFO = 0x1F3A4D      # Bleu nuit

DIVIDER = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
DIVIDER_SHORT = "━━━━━━━━━━━━━━━"

# ═══════════════════════════════════════════════════
# INTENTS (on enlève message_content, pas nécessaire pour slash)
# ═══════════════════════════════════════════════════
intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)


# ═══════════════════════════════════════════════════
# DESIGN HELPERS
# ═══════════════════════════════════════════════════
def zt_embed(title=None, description="", color=COLOR_MAIN, author=None):
    e = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(timezone.utc),
    )
    e.set_footer(text=f"{GANG_NAME}  •  Respect ou rien")
    if author:
        e.set_author(name=author.display_name, icon_url=author.display_avatar.url)
    return e


def dm_embed(title, description="", color=COLOR_MAIN):
    e = discord.Embed(
        title=f"◆  {title}",
        description=description,
        color=color,
        timestamp=datetime.now(timezone.utc),
    )
    e.set_footer(text=f"{GANG_NAME}")
    return e


def progress_bar(current, total, length=20):
    if total == 0:
        return "▱" * length + " 0%"
    filled = int(length * current / total)
    bar = "▰" * filled + "▱" * (length - filled)
    pct = int(100 * current / total)
    return f"`{bar}` **{pct}%**"


def is_staff():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator or interaction.user.guild_permissions.kick_members:
            return True
        await interaction.response.send_message(
            embed=zt_embed("◇  Accès refusé", "Cette commande est réservée au staff.", COLOR_DANGER),
            ephemeral=True,
        )
        return False
    return app_commands.check(predicate)


# ═══════════════════════════════════════════════════
# EVENTS
# ═══════════════════════════════════════════════════
@bot.event
async def on_ready():
    log.info(f"✅ Connecté en tant que {bot.user} (id: {bot.user.id})")
    log.info(f"📊 Présent sur {len(bot.guilds)} serveur(s)")
    for g in bot.guilds:
        log.info(f"   • {g.name} (id: {g.id}, {g.member_count} membres)")

    try:
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            log.info(f"⚡ {len(synced)} commandes sync INSTANTANÉ sur serveur {GUILD_ID}")
        else:
            synced = await bot.tree.sync()
            log.info(f"🌍 {len(synced)} commandes GLOBALES sync (visible sous 1h max)")
            for g in bot.guilds:
                try:
                    bot.tree.copy_global_to(guild=g)
                    s = await bot.tree.sync(guild=g)
                    log.info(f"   ⚡ {len(s)} commandes sync instantané sur '{g.name}'")
                except Exception as e:
                    log.warning(f"   ⚠️ Sync échouée sur '{g.name}': {e}")
    except Exception as e:
        log.exception(f"❌ Erreur sync: {e}")

    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name=f"sur {GANG_NAME}"),
        status=discord.Status.dnd,
    )


@bot.event
async def on_member_join(member: discord.Member):
    channel = discord.utils.find(
        lambda c: c.name in ("bienvenue", "welcome", "général", "general", "accueil"),
        member.guild.text_channels,
    )
    if channel and channel.permissions_for(member.guild.me).send_messages:
        embed = zt_embed(color=COLOR_MAIN)
        embed.set_author(
            name="◆  Nouveau membre",
            icon_url=member.guild.icon.url if member.guild.icon else None,
        )
        embed.description = (
            f"{DIVIDER}\n"
            f"### Bienvenue {member.mention}\n"
            f"Tu rejoins **{GANG_NAME}**.\n\n"
            f"`▸` Lis le règlement avec `/regles`\n"
            f"`▸` Présente-toi en quelques mots\n"
            f"`▸` Respect du staff et des membres\n\n"
            f"**Tu es le {member.guild.member_count}ème membre**\n"
            f"{DIVIDER}"
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(embed=embed)


# Sync manuelle via mention : "@bot sync"
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return
    if bot.user in message.mentions and "sync" in message.content.lower():
        if not message.author.guild_permissions.administrator:
            await message.reply("◇ Seul un admin peut forcer la sync.")
            return
        try:
            bot.tree.copy_global_to(guild=message.guild)
            synced = await bot.tree.sync(guild=message.guild)
            await message.reply(
                embed=zt_embed("◆  Sync effectuée",
                               f"**{len(synced)}** commandes synchronisées sur ce serveur.",
                               COLOR_SUCCESS)
            )
        except Exception as e:
            await message.reply(f"◇ Erreur: `{e}`")


# ═══════════════════════════════════════════════════
# /dmall — Commande principale
# ═══════════════════════════════════════════════════
@bot.tree.command(name="dmall", description="Envoie un MP à tous les membres du serveur (Staff)")
@app_commands.describe(
    message="Le message à envoyer",
    titre="Titre du message (optionnel)",
    role="Limiter à un rôle spécifique (optionnel)",
    inclure_bots="Inclure les bots (défaut: non)",
)
@is_staff()
async def dmall(
    interaction: discord.Interaction,
    message: str,
    titre: str = "Communication officielle",
    role: discord.Role | None = None,
    inclure_bots: bool = False,
):
    await interaction.response.defer(ephemeral=True, thinking=True)
    guild = interaction.guild

    targets = role.members if role else guild.members
    if not inclure_bots:
        targets = [m for m in targets if not m.bot]
    targets = [m for m in targets if m.id != bot.user.id]

    if not targets:
        await interaction.followup.send(
            embed=zt_embed("◇  Aucune cible", "Personne à contacter.", COLOR_DANGER),
            ephemeral=True,
        )
        return

    # Embed DM stylé sombre
    dm = dm_embed(titre, color=COLOR_MAIN)
    dm.description = f"{DIVIDER}\n{message}\n{DIVIDER}"
    dm.add_field(name="`▸` Envoyé par", value=interaction.user.mention, inline=True)
    dm.add_field(name="`▸` Serveur", value=guild.name, inline=True)
    if guild.icon:
        dm.set_thumbnail(url=guild.icon.url)

    sent, failed, failed_names = 0, 0, []

    progress_embed = zt_embed(
        "◆  Diffusion en cours",
        f"**Cible:** {len(targets)} membres\n\n{progress_bar(0, len(targets))}\n\n`✓` Envoyés: **0**\n`✗` Échoués: **0**",
        COLOR_INFO,
    )
    progress = await interaction.followup.send(embed=progress_embed, ephemeral=True)

    for i, member in enumerate(targets, start=1):
        try:
            await member.send(embed=dm)
            sent += 1
        except (discord.Forbidden, discord.HTTPException):
            failed += 1
            failed_names.append(member.display_name)

        await asyncio.sleep(1.2)

        if i % 5 == 0 or i == len(targets):
            try:
                progress_embed = zt_embed(
                    "◆  Diffusion en cours",
                    f"**Cible:** {len(targets)} membres\n\n{progress_bar(i, len(targets))}\n\n"
                    f"`✓` Envoyés: **{sent}**\n`✗` Échoués: **{failed}**",
                    COLOR_INFO,
                )
                await progress.edit(embed=progress_embed)
            except discord.HTTPException:
                pass

    result_color = COLOR_SUCCESS if failed == 0 else (COLOR_WARN if sent > failed else COLOR_DANGER)
    result = zt_embed(
        "◆  Diffusion terminée",
        f"{DIVIDER_SHORT}\n"
        f"`✓` **{sent}** MP envoyés avec succès\n"
        f"`✗` **{failed}** échecs (MP fermés)\n"
        f"{DIVIDER_SHORT}",
        result_color,
        author=interaction.user,
    )
    if failed_names and failed <= 25:
        result.add_field(
            name="Membres injoignables",
            value=", ".join(f"`{n}`" for n in failed_names[:25]),
            inline=False,
        )
    await interaction.followup.send(embed=result, ephemeral=True)


# ═══════════════════════════════════════════════════
# MODÉRATION
# ═══════════════════════════════════════════════════
@bot.tree.command(name="ban", description="Bannir un membre du serveur")
@app_commands.describe(membre="Membre à bannir", raison="Raison du bannissement")
@is_staff()
async def ban(interaction: discord.Interaction, membre: discord.Member, raison: str = "Non spécifiée"):
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message(
            embed=zt_embed("◇  Refusé", "Permission `ban_members` manquante.", COLOR_DANGER), ephemeral=True
        )
        return
    try:
        await membre.ban(reason=f"{interaction.user} — {raison}")
        embed = zt_embed("◆  Bannissement", color=COLOR_DANGER, author=interaction.user)
        embed.add_field(name="`▸` Membre", value=f"{membre.mention}\n`{membre}`", inline=True)
        embed.add_field(name="`▸` Raison", value=raison, inline=True)
        embed.set_thumbnail(url=membre.display_avatar.url)
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message(
            embed=zt_embed("◇  Refusé", "Permissions insuffisantes pour ban ce membre.", COLOR_DANGER), ephemeral=True
        )


@bot.tree.command(name="kick", description="Expulser un membre du serveur")
@app_commands.describe(membre="Membre à expulser", raison="Raison de l'expulsion")
@is_staff()
async def kick(interaction: discord.Interaction, membre: discord.Member, raison: str = "Non spécifiée"):
    try:
        await membre.kick(reason=f"{interaction.user} — {raison}")
        embed = zt_embed("◆  Expulsion", color=COLOR_WARN, author=interaction.user)
        embed.add_field(name="`▸` Membre", value=f"{membre.mention}\n`{membre}`", inline=True)
        embed.add_field(name="`▸` Raison", value=raison, inline=True)
        embed.set_thumbnail(url=membre.display_avatar.url)
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message(
            embed=zt_embed("◇  Refusé", "Permissions insuffisantes.", COLOR_DANGER), ephemeral=True
        )


@bot.tree.command(name="mute", description="Rendre muet un membre (timeout Discord)")
@app_commands.describe(membre="Membre à mute", minutes="Durée en minutes (max 40320)", raison="Raison")
@is_staff()
async def mute(interaction: discord.Interaction, membre: discord.Member, minutes: int, raison: str = "Non spécifiée"):
    if minutes < 1 or minutes > 40320:
        await interaction.response.send_message(
            embed=zt_embed("◇  Erreur", "Durée entre 1 et 40320 minutes.", COLOR_DANGER), ephemeral=True
        )
        return
    try:
        until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        await membre.timeout(until, reason=f"{interaction.user} — {raison}")
        embed = zt_embed("◆  Mute", color=COLOR_WARN, author=interaction.user)
        embed.add_field(name="`▸` Membre", value=membre.mention, inline=True)
        embed.add_field(name="`▸` Durée", value=f"`{minutes} min`", inline=True)
        embed.add_field(name="`▸` Raison", value=raison, inline=False)
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message(
            embed=zt_embed("◇  Refusé", "Permissions insuffisantes.", COLOR_DANGER), ephemeral=True
        )


@bot.tree.command(name="unmute", description="Retirer le mute d'un membre")
@app_commands.describe(membre="Membre à démuter")
@is_staff()
async def unmute(interaction: discord.Interaction, membre: discord.Member):
    try:
        await membre.timeout(None, reason=f"Unmute par {interaction.user}")
        await interaction.response.send_message(
            embed=zt_embed("◆  Unmute", f"{membre.mention} peut de nouveau parler.", COLOR_SUCCESS, author=interaction.user)
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            embed=zt_embed("◇  Refusé", "Permissions insuffisantes.", COLOR_DANGER), ephemeral=True
        )


@bot.tree.command(name="clear", description="Supprimer X messages du salon (1-100)")
@app_commands.describe(nombre="Nombre de messages à supprimer")
@is_staff()
async def clear(interaction: discord.Interaction, nombre: int):
    if nombre < 1 or nombre > 100:
        await interaction.response.send_message(
            embed=zt_embed("◇  Erreur", "Nombre entre 1 et 100.", COLOR_DANGER), ephemeral=True
        )
        return
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=nombre)
    await interaction.followup.send(
        embed=zt_embed("◆  Nettoyage", f"**{len(deleted)}** messages supprimés.", COLOR_SUCCESS), ephemeral=True
    )


@bot.tree.command(name="warn", description="Avertir un membre")
@app_commands.describe(membre="Membre à avertir", raison="Raison de l'avertissement")
@is_staff()
async def warn(interaction: discord.Interaction, membre: discord.Member, raison: str):
    embed = zt_embed("◆  Avertissement", color=COLOR_WARN, author=interaction.user)
    embed.add_field(name="`▸` Membre", value=membre.mention, inline=True)
    embed.add_field(name="`▸` Raison", value=raison, inline=False)
    embed.set_thumbnail(url=membre.display_avatar.url)
    await interaction.response.send_message(embed=embed)

    try:
        dm = dm_embed("Avertissement officiel", color=COLOR_WARN)
        dm.description = (
            f"{DIVIDER}\n"
            f"Tu as reçu un **warn** sur **{interaction.guild.name}**.\n\n"
            f"**Raison:** {raison}\n"
            f"{DIVIDER}\n"
            f"Prochaine étape en cas de récidive : `mute` → `kick` → `ban`"
        )
        await membre.send(embed=dm)
    except discord.Forbidden:
        pass


# ═══════════════════════════════════════════════════
# COMMUNICATION
# ═══════════════════════════════════════════════════
@bot.tree.command(name="annonce", description="Faire une annonce officielle ZT")
@app_commands.describe(titre="Titre de l'annonce", message="Contenu", salon="Salon de destination")
@is_staff()
async def annonce(
    interaction: discord.Interaction,
    titre: str,
    message: str,
    salon: discord.TextChannel | None = None,
):
    target = salon or interaction.channel
    embed = zt_embed(color=COLOR_MAIN, author=interaction.user)
    embed.description = (
        f"# ◆ {titre}\n"
        f"{DIVIDER}\n"
        f"{message}\n"
        f"{DIVIDER}"
    )
    if interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    await target.send(content="@everyone", embed=embed, allowed_mentions=discord.AllowedMentions(everyone=True))
    await interaction.response.send_message(
        embed=zt_embed("◆  Annonce postée", f"Diffusée dans {target.mention}", COLOR_SUCCESS),
        ephemeral=True,
    )


@bot.tree.command(name="rapport", description="Envoyer un rapport au staff")
@app_commands.describe(sujet="Sujet du rapport", details="Détails")
async def rapport(interaction: discord.Interaction, sujet: str, details: str):
    salon = discord.utils.find(
        lambda c: c.name in ("rapports", "staff", "logs", "rapport"),
        interaction.guild.text_channels,
    )
    if not salon:
        await interaction.response.send_message(
            embed=zt_embed("◇  Erreur", "Aucun salon `#rapports` configuré.", COLOR_DANGER),
            ephemeral=True,
        )
        return
    embed = zt_embed(color=COLOR_WARN, author=interaction.user)
    embed.description = (
        f"# ◆ Rapport — {sujet}\n"
        f"{DIVIDER}\n"
        f"{details}\n"
        f"{DIVIDER}"
    )
    embed.add_field(name="`▸` Envoyé par", value=interaction.user.mention, inline=True)
    embed.add_field(name="`▸` Depuis", value=interaction.channel.mention, inline=True)
    await salon.send(embed=embed)
    await interaction.response.send_message(
        embed=zt_embed("◆  Rapport envoyé", "Le staff a été notifié.", COLOR_SUCCESS),
        ephemeral=True,
    )


# ═══════════════════════════════════════════════════
# GESTION GANG
# ═══════════════════════════════════════════════════
@bot.tree.command(name="regles", description="Afficher le règlement du gang ZT")
async def regles(interaction: discord.Interaction):
    embed = zt_embed(color=COLOR_MAIN)
    embed.set_author(name=f"◆  Règlement — {GANG_NAME}")
    embed.description = (
        f"{DIVIDER}\n"
        f"Le respect du règlement n'est **pas optionnel**.\n"
        f"**Zéro Tolérance.**\n"
        f"{DIVIDER}\n\n"
        f"`I.` **Respect**\n"
        f"Aucune insulte gratuite entre membres du gang.\n\n"
        f"`II.` **Discrétion**\n"
        f"Ce qui se passe dans ZT reste dans ZT.\n\n"
        f"`III.` **Loyauté**\n"
        f"Pas de trahison. Pas de double allégeance.\n\n"
        f"`IV.` **Présence**\n"
        f"Réponds aux appels et opérations du gang.\n\n"
        f"`V.` **Hiérarchie**\n"
        f"Respect du chef et des lieutenants.\n\n"
        f"{DIVIDER}\n"
        f"**Sanctions:** `warn` → `mute` → `kick` → `ban`"
    )
    if interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="recrue", description="Officialiser un nouveau membre du gang")
@app_commands.describe(membre="Le nouveau membre", role="Rôle ZT à attribuer")
@is_staff()
async def recrue(interaction: discord.Interaction, membre: discord.Member, role: discord.Role):
    try:
        await membre.add_roles(role, reason=f"Recrutement par {interaction.user}")
        embed = zt_embed(color=COLOR_SUCCESS, author=interaction.user)
        embed.description = (
            f"# ◆ Nouvelle recrue\n"
            f"{DIVIDER}\n"
            f"**{membre.mention}** rejoint officiellement **{GANG_NAME}**.\n"
            f"{DIVIDER}\n\n"
            f"`▸` **Rôle attribué :** {role.mention}\n"
            f"`▸` **Parrain :** {interaction.user.mention}"
        )
        embed.set_thumbnail(url=membre.display_avatar.url)
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message(
            embed=zt_embed("◇  Refusé", "Permissions insuffisantes.", COLOR_DANGER), ephemeral=True
        )


@bot.tree.command(name="promotion", description="Promouvoir un membre à un rôle supérieur")
@app_commands.describe(membre="Membre", nouveau_role="Nouveau rôle", ancien_role="Ancien rôle (optionnel)")
@is_staff()
async def promotion(
    interaction: discord.Interaction,
    membre: discord.Member,
    nouveau_role: discord.Role,
    ancien_role: discord.Role | None = None,
):
    try:
        await membre.add_roles(nouveau_role, reason=f"Promotion par {interaction.user}")
        if ancien_role and ancien_role in membre.roles:
            await membre.remove_roles(ancien_role)
        embed = zt_embed(color=COLOR_ACCENT, author=interaction.user)
        embed.description = (
            f"# ◆ Promotion\n"
            f"{DIVIDER}\n"
            f"**{membre.mention}** monte en grade.\n"
            f"{DIVIDER}\n\n"
            f"`▸` **Nouveau rôle :** {nouveau_role.mention}\n"
            + (f"`▸` **Ancien rôle retiré :** {ancien_role.mention}" if ancien_role else "")
        )
        embed.set_thumbnail(url=membre.display_avatar.url)
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message(
            embed=zt_embed("◇  Refusé", "Permissions insuffisantes.", COLOR_DANGER), ephemeral=True
        )


@bot.tree.command(name="membres", description="Statistiques du serveur")
async def membres(interaction: discord.Interaction):
    g = interaction.guild
    humans = sum(1 for m in g.members if not m.bot)
    bots = sum(1 for m in g.members if m.bot)
    online = sum(1 for m in g.members if m.status != discord.Status.offline and not m.bot)

    embed = zt_embed(color=COLOR_MAIN)
    embed.set_author(name=f"◆  {g.name}", icon_url=g.icon.url if g.icon else None)
    embed.description = (
        f"{DIVIDER}\n"
        f"`▸` **Total :** `{g.member_count}` membres\n"
        f"`▸` **Humains :** `{humans}`\n"
        f"`▸` **Bots :** `{bots}`\n"
        f"`▸` **En ligne :** `{online}`\n"
        f"{DIVIDER}\n"
        f"`▸` **Salons :** `{len(g.channels)}`\n"
        f"`▸` **Rôles :** `{len(g.roles)}`\n"
        f"`▸` **Créé le :** <t:{int(g.created_at.timestamp())}:D>"
    )
    if g.icon:
        embed.set_thumbnail(url=g.icon.url)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="help", description="Liste toutes les commandes du bot ZT")
async def help_cmd(interaction: discord.Interaction):
    embed = zt_embed(color=COLOR_MAIN)
    embed.set_author(name=f"◆  Commandes — {GANG_NAME}")
    embed.description = (
        f"{DIVIDER}\n"
        f"### `▸` Communication\n"
        f"`/dmall` — MP à tous les membres\n"
        f"`/annonce` — Annonce officielle\n"
        f"`/rapport` — Envoyer un rapport au staff\n\n"
        f"### `▸` Modération\n"
        f"`/ban` `/kick` `/mute` `/unmute` `/warn` `/clear`\n\n"
        f"### `▸` Gang\n"
        f"`/recrue` — Officialiser un membre\n"
        f"`/promotion` — Monter en grade\n"
        f"`/regles` — Règlement\n"
        f"`/membres` — Stats du serveur\n"
        f"{DIVIDER}"
    )
    if interaction.guild and interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ═══════════════════════════════════════════════════
# ERROR HANDLER
# ═══════════════════════════════════════════════════
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        return
    log.exception(f"Erreur commande: {error}")
    try:
        msg = zt_embed("◇  Erreur", f"`{error}`", COLOR_DANGER)
        if interaction.response.is_done():
            await interaction.followup.send(embed=msg, ephemeral=True)
        else:
            await interaction.response.send_message(embed=msg, ephemeral=True)
    except discord.HTTPException:
        pass


# ═══════════════════════════════════════════════════
# LANCEMENT
# ═══════════════════════════════════════════════════
if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN manquant dans les variables d'environnement.")
    bot.run(TOKEN, log_handler=None
