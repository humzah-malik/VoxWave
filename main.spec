# main.spec
block_cipher = None

a = Analysis(['main.py'],
             pathex=['.'],
             binaries=[],
             datas=[],
             hiddenimports=['spotipy.oauth2'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

app = BUNDLE(pyz,
             a.scripts,
             a.binaries,
             a.zipfiles,
             a.datas,
             name='HandVoiceControl',
             icon=None,
             bundle_identifier='com.yourname.handvoicecontrol')