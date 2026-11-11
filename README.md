# CFD Automation — SALOME GEOM + SMESH → BARAM

Bu herkese açık depo, **FreeCAD kullanmadan** SALOME ile geometri ve mesh üretme, ardından BARAM/NextFOAM ortamına aktarma testleri içindir.

## İlk geometri
- Dikey boru akış hacmi: **50 mm iç çap, 5000 mm uzunluk**
- SALOME GEOM: `MakeCylinderRH(25.0, 5000.0)` (mm)
- SALOME SMESH: NETGEN tetrahedral mesh; `inlet`, `outlet`, `wall` grupları
- Hedef dosya: `outputs/pipe_50mm_5m.unv`
- Mesh boyutları CFD'ye alınırken **mm → m ölçeklenmelidir (0,001)**.

## Durum ve güvenlik
- FreeCAD indirme ve test dosyaları projeden çıkarıldı.
- `tests/salome_mesh_pipe.py` SALOME Python ortamında çalıştırılmak üzere hazırlandı; henüz gerçek SALOME ortamında mesh doğrulanmadı.
- GitHub-hosted Windows sanal makineleri geçicidir; her çalışma sonrasında sıfırlanır.
- Özel/geçerli mühendislik verileri veya kimlik bilgileri bu public depoya yüklenmemelidir.
- BARAM CFD çözümü, gerçek mesh ve sınır şartları doğrulanmadan başlatılmamalıdır.
