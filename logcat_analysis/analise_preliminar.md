# Relatório de Análise de Logcat - Android Automotive OS (AAOS)

- **Origem dos logs:** `aaos_logcat_latest.log`
- **Janela temporal:** `09-17 17:18:31.890` até `09-17 17:27:49.407`
- **Total de eventos estruturados:** **44,776** (100.0% das linhas do logcat)
- **Total de processos identificados:** **613**
- **Total de tags únicas mapeadas:** **1,705** (com processos detalhados em [`tags_resumo.csv`](./tags_resumo.csv))

## 1. Distribuição por Severidade (Log Level)

| Nível | Nome | Quantidade de Eventos | Porcentagem |
| :---: | :--- | :---: | :---: |
| `V` | **VERBOSE** | 6,384 | 14.26% |
| `D` | **DEBUG** | 15,834 | 35.36% |
| `I` | **INFO** | 13,946 | 31.15% |
| `W` | **WARN** | 6,115 | 13.66% |
| `E` | **ERROR** | 2,497 | 5.58% |
| `F` | **FATAL** | 0 | 0.00% |

## 2. Categorização de Eventos

Todos os eventos estruturados foram classificados em categorias temáticas. As linhas que não se enquadram diretamente em regras específicas de segurança ou automotivas são agrupadas na categoria genérica **`Outros / Serviços Gerais do SO`**, garantindo que nenhum log passe despercebido.

| Categoria | Total de Eventos | % do Total | Descrição / Escopo |
| :--- | :---: | :---: | :--- |
| **Outros / Serviços Gerais do SO** | 27,508 | 61.43% | Eventos não categorizados em nenhuma categoria anterior. |
| **Gestão de Usuários e Acesso** | 7,578 | 16.92% | Perfis de usuário (motorista/passageiro), permissões de apps e contas. |
| **Subssistema Automotivo (AAOS)** | 5,304 | 11.85% | Barramentos veiculares, HVAC, CarService, Vehicle HAL (VHAL), Cluster e telemetria. |
| **Auditoria e SELinux** | 2,239 | 5.00% | Daemon de auditoria do kernel (auditd), checagem de AVC denials e políticas SELinux. |
| **Criptografia e Chaves** | 1,003 | 2.24% | Keystore2, KeyMint, File-Based Encryption (FBE) e montagem de storage (vold). |
| **Rede e Conexões** | 999 | 2.23% | Roteamento de rede (netd), DNS (resolv), regras de iptables e conexões de depuração (adbd). |
| **Integridade e Estabilidade** | 145 | 0.32% | Encerramento forçado de processos, ANR, tombstone de crashes e LowMemoryKiller (PSI). |

## 3. Rastreabilidade de Processos Iniciados (Zygote & Sistema)

> [!TIP]
> **O Presente Especial do Zygote:** O daemon raiz do Android registra explicitamente cada processo iniciado com a mensagem `Process <PID> created for <process_name>`. Isso nos permite correlacionar PIDs com seus pacotes e processos reais (ex: `com.android.car`, `android.car.cluster`, `com.android.systemui`), eliminando ambiguidades entre serviços do sistema e APIs veiculares.

### 3.1 Top 15 Processos por Volume de Logs Emitidos

| # | Processo / Pacote | Total de Eventos | % do Total |
| :-: | :--- | :-: | :-: |
| 1 | `system_server` | 17,831 | 39.82% |
| 2 | `com.android.phone` | 4,734 | 10.57% |
| 3 | `servicemanager` | 3,456 | 7.72% |
| 4 | `auditd` | 2,358 | 5.27% |
| 5 | `com.android.systemui` | 2,265 | 5.06% |
| 6 | `com.android.bluetooth` | 1,305 | 2.91% |
| 7 | `com.android.car` | 1,139 | 2.54% |
| 8 | `com.android.providers.media.module` | 1,033 | 2.31% |
| 9 | `audioserver` | 551 | 1.23% |
| 10 | `vold_prepare_subdirs` | 538 | 1.20% |
| 11 | `zygote64` | 520 | 1.16% |
| 12 | `android.hardware.audio.service` | 406 | 0.91% |
| 13 | `netd` | 400 | 0.89% |
| 14 | `artd` | 388 | 0.87% |
| 15 | `android.process.acore` | 363 | 0.81% |

### 3.2 Principais Aplicações e Serviços Automotivos Rastreados

| PID | Pacote / Processo | Papel no Android Automotive |
| :-: | :--- | :--- |
| `3025` | `com.android.car` | CarService - Serviço central de controle e barramentos do veículo |
| `3199` | `com.google.android.car.samplerearviewservice` | Câmera de ré / Visão traseira (Rear View Camera) |
| `3214` | `com.android.systemui` | Interface do sistema (barra de status veicular, HVAC e notificações) |
| `3230` | `com.android.car.settings` | Configurações Veiculares (ar-condicionado, segurança, portas, energia) |
| `3328` | `com.android.car` | CarService - Serviço central de controle e barramentos do veículo |
| `3470` | `com.android.car.carlauncher` | Car Launcher - Interface gráfica principal do painel de infoentretenimento |
| `3567` | `com.android.car.rotary` | Controlador físico giratório do console central |
| `4019` | `com.android.car.media` | Mídia e Áudio automotivo multi-zona |
| `4138` | `com.android.car.radio` | Sintonizador de Rádio AM/FM/DAB |
| `4592` | `android.car.cluster` | Instrument Cluster - Painel digital de instrumentos (velocímetro, RPM, marcha) |

```bash
# Listar todos os processos criados pelo Zygote no boot
grep "Zygote  : Process" logcat_analysis/logs/aaos_logcat_latest.log | awk '{print "PID:", $3, "->", $9}'
```

## 4. Comandos Úteis para Filtrar e Inspecionar Cada Categoria

Para explorar interativamente os logs de cada categoria a partir da raiz do repositório, utilize os comandos abaixo:

### Outros / Serviços Gerais do SO (27,508 eventos)
- **Top tags componentes:** `SystemServerTiming` (2212), `init` (987), `PackageManager` (948), `ContextImpl` (678), `libbinder.BackendUnifiedServiceManager` (638)
- **Comando para inspeção:**
```bash
grep -E "SystemServerTiming|ContextImpl|GraphicsEnvironment" logcat_analysis/logs/aaos_logcat_latest.log | head -n 20
```

### Gestão de Usuários e Acesso (7,578 eventos)
- **Top tags componentes:** `SystemServerTimingAsync` (3529), `AccessibilityUserState` (548), `sysui_multi_action` (438), `SystemServerTiming` (296), `SystemConfig` (135)
- **Comando para inspeção:**
```bash
grep -E "PackageManager|PermissionController|UserManager" logcat_analysis/logs/aaos_logcat_latest.log | head -n 20
```

### Subssistema Automotivo (AAOS) (5,304 eventos)
- **Top tags componentes:** `HvacController` (790), `SubscriptionManager` (371), `SatelliteController` (273), `CAR.POWER` (120), `StorageManagerService` (108)
- **Comando para inspeção:**
```bash
grep -E "HvacController|CarService|VehicleHAL|IVehicle" logcat_analysis/logs/aaos_logcat_latest.log | head -n 20
```

### Auditoria e SELinux (2,239 eventos)
- **Top tags componentes:** `auditd` (1361), `keystore2` (170), `SystemServerTimingAsync` (86), `iptables-restor` (70), `SELinux` (64)
- **Comando para inspeção:**
```bash
grep -E "auditd|avc|selinux" logcat_analysis/logs/aaos_logcat_latest.log | head -n 20
```

### Criptografia e Chaves (1,003 eventos)
- **Top tags componentes:** `vold_prepare_subdirs` (487), `vold` (183), `init` (71), `nativeloader` (53), `BluetoothKeystoreService` (34)
- **Comando para inspeção:**
```bash
grep -E "keystore|keymint|vold|fscrypt" logcat_analysis/logs/aaos_logcat_latest.log | head -n 20
```

### Rede e Conexões (999 eventos)
- **Top tags componentes:** `resolv` (267), `InetDiagMessage` (210), `adbd` (119), `netd` (107), `NetBpfLoad` (53)
- **Comando para inspeção:**
```bash
grep -E "netd|resolv|adbd|iptables" logcat_analysis/logs/aaos_logcat_latest.log | head -n 20
```

### Integridade e Estabilidade (145 eventos)
- **Top tags componentes:** `mediaextractor` (24), `SystemServerTiming` (24), `mediaswcodec` (19), `lowmemorykiller` (8), `PackageManager` (8)
- **Comando para inspeção:**
```bash
grep -E "lowmemorykiller|crash|tombstone|anr" logcat_analysis/logs/aaos_logcat_latest.log | head -n 20
```

## 5. Top 20 Componentes / Tags Mais Frequentes

| # | Tag / Componente | Eventos | % do Total |
| :-: | :--- | :-: | :-: |
| 1 | `SystemServerTimingAsync` | 3,675 | 8.21% |
| 2 | `SystemServerTiming` | 2,594 | 5.79% |
| 3 | `auditd` | 1,361 | 3.04% |
| 4 | `init` | 1,204 | 2.69% |
| 5 | `PackageManager` | 1,178 | 2.63% |
| 6 | `SatelliteController` | 811 | 1.81% |
| 7 | `HvacController` | 790 | 1.76% |
| 8 | `ContextImpl` | 736 | 1.64% |
| 9 | `libbinder.BackendUnifiedServiceManager` | 729 | 1.63% |
| 10 | `nativeloader` | 677 | 1.51% |
| 11 | `sysui_multi_action` | 636 | 1.42% |
| 12 | `AccessibilityUserState` | 548 | 1.22% |
| 13 | `vold_prepare_subdirs` | 538 | 1.20% |
| 14 | `GraphicsEnvironment` | 510 | 1.14% |
| 15 | `StorageManagerService` | 500 | 1.12% |
| 16 | `SystemServiceRegistry` | 459 | 1.03% |
| 17 | `libprocessgroup` | 450 | 1.01% |
| 18 | `StrictMode` | 427 | 0.95% |
| 19 | `SubscriptionManager` | 420 | 0.94% |
| 20 | `Zygote` | 393 | 0.88% |
## 6. Análise de Alertas e Erros (`ERROR` & `WARN`)

### Principais fontes de `ERROR` (Total: 2,497)

| Componente | Quantidade de Erros |
| :--- | :---: |
| `SystemServiceRegistry` | 456 |
| `AppOpService` | 209 |
| `StrictMode` | 156 |
| `DevicePolicyEngine` | 154 |
| `ConstraintLayout` | 104 |
| `CarrierPrivilegesTracker` | 95 |
| `ConnectivitySettingsManager` | 71 |
| `Cluster.ViewModel` | 69 |
| `MESA` | 60 |
| `Binder` | 54 |

```bash
# Inspecionar os 20 últimos erros gravados no logcat
grep " E " logcat_analysis/logs/aaos_logcat_latest.log | tail -n 20
```

### Principais fontes de `WARN` (Total: 6,115)

| Componente | Quantidade de Avisos |
| :--- | :---: |
| `libbinder.BackendUnifiedServiceManager` | 729 |
| `ContextImpl` | 704 |
| `auditd` | 527 |
| `PackageManager` | 440 |
| `ModernMediaScanner` | 296 |
| `Zygote` | 191 |
| `libc` | 156 |
| `idmap2d` | 156 |
| `FileUtils` | 134 |
| `BestClock` | 128 |

```bash
# Inspecionar os 20 últimos warnings gravados no logcat
grep " W " logcat_analysis/logs/aaos_logcat_latest.log | tail -n 20
```

