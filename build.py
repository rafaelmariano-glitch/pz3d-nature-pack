"""Gera o mod pronto em dist/: pasta do mod, zip para o release e estrutura para a Steam Workshop.

    python build.py            # gera tudo
    python build.py --install  # gera e copia para %USERPROFILE%/Zomboid/mods (para testar)

Requer Python 3.10+, Pillow e numpy (pip install pillow numpy).
"""
import os, shutil, subprocess, sys, zipfile
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
MOD_ID = 'pz3d_naturepack'
VERSION = '0.11.0'
DIST = os.path.join(ROOT, 'dist')
MOD = os.path.join(DIST, MOD_ID)
PREVIEW = os.path.join(ROOT, 'docs', 'preview_models.png')


def poster(src, dst, size):
    """capa quadrada: recorte da previa dos modelos com o nome do pack."""
    im = Image.open(src).convert('RGB')
    w, h = im.size
    side = min(w, h)
    im = im.crop(((w - side) // 2, 0, (w - side) // 2 + side, side)).resize((size, size), Image.LANCZOS)
    dr = ImageDraw.Draw(im)
    try:
        f = ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf', size // 9)
    except OSError:
        f = ImageFont.load_default()
    band = size // 5
    dr.rectangle([0, size - band, size, size], fill=(20, 40, 24))
    dr.text((size / 2, size - band / 2), 'pz3d Nature Pack', font=f, fill=(235, 240, 230), anchor='mm')
    im.save(dst)


def main():
    shutil.rmtree(MOD, ignore_errors=True)
    os.makedirs(os.path.dirname(PREVIEW), exist_ok=True)
    # previa da documentacao: uma selecao que representa cada grupo de modelos
    env = dict(os.environ, PREVIEW_COLS='6', PREVIEW_CELL='260', PREVIEW_EXACT='1', PREVIEW_ONLY=','.join([
        'arbusto_grande_verde', 'arbusto_grande_roxo', 'arbusto_medio_outono', 'moita_galhos_grande',
        'sebe_alta', 'sebe_bola', 'sebe_cone', 'muda_pinheiro', 'muda_pinheiro_neve', 'muda_folhosa_vermelho_out',
        'muda_folhosa_olaia_flor', 'muda_betula_ouro_out', 'grama_alta_verao', 'grama_media_seca', 'samambaia_grande',
        'planta_folha_larga', 'planta_alta', 'folhas_secas_0', 'pedra_media_1', 'laje_2', 'chao_grama_escura',
        'chao_terra', 'placa_westpoint_esq_esq_py', 'placa_curva_dir_py', 'placa_pare_px', 'placa_zigue_px']))
    subprocess.check_call([sys.executable, os.path.join(ROOT, 'generator', 'make_pack.py'), MOD, PREVIEW], env=env)
    # capa: 3x3 com os modelos mais vistosos
    hero = os.path.join(DIST, '_capa.png')
    env_h = dict(os.environ, PREVIEW_COLS='3', PREVIEW_CELL='300', PREVIEW_EXACT='1', PREVIEW_ONLY=','.join([
        'arbusto_grande_verde', 'muda_folhosa_vermelho_out', 'muda_pinheiro', 'sebe_bola', 'muda_folhosa_olaia_flor',
        'samambaia_grande', 'grama_alta_verao', 'pedra_media_1', 'placa_curva_dir_py']))
    import tempfile
    tmp_mod = tempfile.mkdtemp(prefix='pz3d_capa_')
    subprocess.check_call([sys.executable, os.path.join(ROOT, 'generator', 'make_pack.py'), tmp_mod, hero], env=env_h)
    shutil.rmtree(tmp_mod, ignore_errors=True)
    poster(hero, os.path.join(MOD, '42', 'poster.png'), 512)

    # zip para o release do GitHub: a pasta do mod pronta para Zomboid/mods
    zpath = os.path.join(DIST, f'{MOD_ID}-v{VERSION}.zip')
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
        for base, _, files in os.walk(MOD):
            for fn in files:
                full = os.path.join(base, fn)
                z.write(full, os.path.relpath(full, DIST))
    print('zip:', zpath)

    # estrutura da Steam Workshop (subir pelo menu do jogo: Workshop > Criar/Atualizar item)
    ws = os.path.join(DIST, 'workshop', 'pz3dNaturePack')
    shutil.rmtree(ws, ignore_errors=True)
    shutil.copytree(MOD, os.path.join(ws, 'Contents', 'mods', MOD_ID))
    poster(hero, os.path.join(ws, 'preview.png'), 256)
    os.remove(hero)
    print('workshop:', ws)

    if '--install' in sys.argv:
        dst = os.path.join(os.path.expanduser('~'), 'Zomboid', 'mods', MOD_ID)
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(MOD, dst)
        print('instalado em', dst)


if __name__ == '__main__':
    main()
