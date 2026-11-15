"""Atualiza o item da Steam Workshop (capa e conteudo) pela Steam ja logada, sem abrir o jogo.

    python tools/workshop_update.py <pasta_do_item_workshop> "nota da mudanca"

A pasta e a que o jogo usa (Zomboid/Workshop/<nome>): precisa de workshop.txt com id=,
preview.png e Contents/. Usa o steam_api64.dll do Project Zomboid (app 108600).
So funciona para o dono do item, com o cliente da Steam aberto e logado.
"""
import ctypes as C, os, shutil, sys, tempfile, time

APP = 108600
DLL = r'C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid\steam_api64.dll'
STATUS = {0: 'concluido', 1: 'preparando', 2: 'preparando conteudo', 3: 'enviando conteudo',
          4: 'enviando capa', 5: 'gravando'}


def main(folder, note):
    meta = dict(l.split('=', 1) for l in open(os.path.join(folder, 'workshop.txt'), encoding='utf-8').read().splitlines() if '=' in l)
    item = int(meta['id'])
    preview = os.path.abspath(os.path.join(folder, 'preview.png'))
    content = os.path.abspath(os.path.join(folder, 'Contents'))

    work = tempfile.mkdtemp(prefix='ws_')     # a Steam le steam_appid.txt da pasta atual
    shutil.copy(DLL, work)
    open(os.path.join(work, 'steam_appid.txt'), 'w').write(str(APP))
    os.chdir(work)
    api = C.CDLL(os.path.join(work, 'steam_api64.dll'))
    err = C.create_string_buffer(1024)
    api.SteamAPI_InitFlat.restype = C.c_int
    r = api.SteamAPI_InitFlat(err)
    if r != 0:
        sys.exit(f'Steam nao iniciou ({r}): {err.value.decode(errors="replace")}')
    api.SteamAPI_SteamUGC_v021.restype = C.c_void_p
    api.SteamAPI_SteamUtils_v010.restype = C.c_void_p
    ugc, utils = api.SteamAPI_SteamUGC_v021(), api.SteamAPI_SteamUtils_v010()
    f = api.SteamAPI_ISteamUGC_StartItemUpdate
    f.restype, f.argtypes = C.c_uint64, [C.c_void_p, C.c_uint32, C.c_uint64]
    h = f(ugc, APP, item)
    for name, val in (('SetItemContent', content), ('SetItemPreview', preview)):
        g = getattr(api, 'SteamAPI_ISteamUGC_' + name)
        g.restype, g.argtypes = C.c_bool, [C.c_void_p, C.c_uint64, C.c_char_p]
        if not g(ugc, h, val.encode('utf-8')):
            sys.exit(name + ' falhou')
    s = api.SteamAPI_ISteamUGC_SubmitItemUpdate
    s.restype, s.argtypes = C.c_uint64, [C.c_void_p, C.c_uint64, C.c_char_p]
    call = s(ugc, h, note.encode('utf-8'))

    done = api.SteamAPI_ISteamUtils_IsAPICallCompleted
    done.restype, done.argtypes = C.c_bool, [C.c_void_p, C.c_uint64, C.POINTER(C.c_bool)]
    prog = api.SteamAPI_ISteamUGC_GetItemUpdateProgress
    prog.restype, prog.argtypes = C.c_int, [C.c_void_p, C.c_uint64, C.POINTER(C.c_uint64), C.POINTER(C.c_uint64)]
    failed = C.c_bool(False); a, b = C.c_uint64(), C.c_uint64(); last = None
    t0 = time.time()
    while not done(utils, call, C.byref(failed)):
        api.SteamAPI_RunCallbacks()
        st = prog(ugc, h, C.byref(a), C.byref(b))
        msg = f'{STATUS.get(st, st)} {a.value}/{b.value}'
        if msg != last: print(msg, flush=True); last = msg
        if time.time() - t0 > 900: sys.exit('tempo esgotado')
        time.sleep(0.5)

    class Result(C.Structure):     # SubmitItemUpdateResult_t
        _fields_ = [('result', C.c_int), ('needs_legal', C.c_bool), ('item', C.c_uint64)]
    res = Result()
    gr = api.SteamAPI_ISteamUtils_GetAPICallResult
    gr.restype = C.c_bool
    gr.argtypes = [C.c_void_p, C.c_uint64, C.c_void_p, C.c_int, C.c_int, C.POINTER(C.c_bool)]
    ok = gr(utils, call, C.byref(res), C.sizeof(res), 3404, C.byref(failed))
    api.SteamAPI_Shutdown()
    print(f'resultado={res.result} (1 = OK)  precisa_aceitar_acordo={res.needs_legal}  item={res.item or item}  leitura_ok={ok}')
    sys.exit(0 if res.result == 1 else 1)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else 'Update')
