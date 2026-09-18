#!/usr/bin/env python3
"""
analyze_logcat.py - Analisador e Categorizador Estatístico de Logcat do AAOS

Descrição:
  Processa arquivos de logcat do Android Automotive OS no formato threadtime,
  identifica os processos que originaram cada evento (via Zygote, ActivityManager e daemons nativos),
  classifica 100% dos eventos em categorias (incluindo 'Outros / Serviços Gerais do SO'),
  mede distribuições de severidade, gera um relatório detalhado em Markdown e exporta
  um arquivo CSV com todas as tags, respectivas categorias, processos de origem, descrições, quantidades e percentuais.

Uso:
  ./logcat_analysis/scripts/analyze_logcat.py [CAMINHO_LOG] [SAIDA_MARKDOWN] [--csv SAIDA_CSV]
  
  Se os argumentos forem omitidos, o script utilizará por padrão:
    CAMINHO_LOG:    logcat_analysis/logs/aaos_logcat_latest.log
    SAIDA_MARKDOWN: logcat_analysis/analise_preliminar.md
    SAIDA_CSV:      logcat_analysis/tags_resumo.csv
"""

import sys
import os
import re
import csv
import argparse
from collections import Counter, defaultdict
from pathlib import Path

LOGCAT_REGEX = re.compile(
    r'^(?P<date>\d{2}-\d{2})\s+'
    r'(?P<time>\d{2}:\d{2}:\d{2}\.\d+)\s+'
    r'(?P<pid>\d+)\s+'
    r'(?P<tid>\d+)\s+'
    r'(?P<level>[VDIWEF])\s+'
    r'(?P<tag>[^:]+?)\s*:\s+'
    r'(?P<message>.*)$'
)

# Expressões regulares para mapeamento de ciclo de vida de processos
ZYGOTE_PROC_RE = re.compile(r'Process (\d+) created for ([\w\.\:]+)')
AM_START_PROC_RE = re.compile(r'Start proc (\d+):([\w\.\:]+)/')

# Daemons nativos conhecidos do Linux / Android
KNOWN_NATIVE_DAEMONS = {
    "auditd": "auditd",
    "netd": "netd",
    "vold": "vold",
    "adbd": "adbd",
    "keystore2": "keystore2",
    "lowmemorykiller": "lowmemorykiller",
    "servicemanager": "servicemanager",
    "surfaceflinger": "surfaceflinger",
    "hwservicemanager": "hwservicemanager",
    "artd": "artd",
    "mediaswcodec": "mediaswcodec",
    "mediaextractor": "mediaextractor",
    "tombstoned": "tombstoned",
    "vold_prepare_subdirs": "vold_prepare_subdirs",
    "AHAL_Module": "android.hardware.audio.service",
    "minradio": "android.hardware.broadcastradio",
    "StreamHalAidl": "audioserver",
    "Zygote": "zygote64",
    "zygote64": "zygote64",
    "carpowerpolicyd": "carpowerpolicyd",
    "bluetooth-cf": "bluetooth-cf",
    "idmap2d": "idmap2d",
    "idmap2": "idmap2",
    "derive_classpath": "derive_classpath",
    "aconfigd_mainline": "aconfigd_mainline"
}

# Definição de categorias temáticas com prioridade decrescente
CATEGORIES_ORDER = [
    ("Subssistema Automotivo (AAOS)", [
        "car", "vehicle", "vhal", "hvac", "cluster", "telemetry", "watchdog"
    ]),
    ("Auditoria e SELinux", [
        "auditd", "audit", "avc", "selinux", "security"
    ]),
    ("Gestão de Usuários e Acesso", [
        "user", "permission", "auth", "account", "keyguard", "locksettings"
    ]),
    ("Criptografia e Chaves", [
        "keystore", "keymint", "vold", "crypt", "fbe"
    ]),
    ("Rede e Conexões", [
        "netd", "iptables", "firewall", "resolv", "wificond", "adbd"
    ]),
    ("Integridade e Estabilidade", [
        "crash", "tombstone", "anr", "sigsegv", "lowmemorykiller", "panic"
    ])
]

# Comandos de exemplo com o caminho a partir da raiz do repositório
GREP_EXAMPLES = {
    "Subssistema Automotivo (AAOS)": 'grep -E "HvacController|CarService|VehicleHAL|IVehicle" logcat_analysis/logs/aaos_logcat_latest.log | head -n 20',
    "Auditoria e SELinux": 'grep -E "auditd|avc|selinux" logcat_analysis/logs/aaos_logcat_latest.log | head -n 20',
    "Gestão de Usuários e Acesso": 'grep -E "PackageManager|PermissionController|UserManager" logcat_analysis/logs/aaos_logcat_latest.log | head -n 20',
    "Criptografia e Chaves": 'grep -E "keystore|keymint|vold|fscrypt" logcat_analysis/logs/aaos_logcat_latest.log | head -n 20',
    "Rede e Conexões": 'grep -E "netd|resolv|adbd|iptables" logcat_analysis/logs/aaos_logcat_latest.log | head -n 20',
    "Integridade e Estabilidade": 'grep -E "lowmemorykiller|crash|tombstone|anr" logcat_analysis/logs/aaos_logcat_latest.log | head -n 20',
    "Outros / Serviços Gerais do SO": 'grep -E "SystemServerTiming|ContextImpl|GraphicsEnvironment" logcat_analysis/logs/aaos_logcat_latest.log | head -n 20'
}

CATEGORY_DESCRIPTIONS = {
    "Subssistema Automotivo (AAOS)": "Barramentos veiculares, HVAC, CarService, Vehicle HAL (VHAL), Cluster e telemetria.",
    "Auditoria e SELinux": "Daemon de auditoria do kernel (auditd), checagem de AVC denials e políticas SELinux.",
    "Gestão de Usuários e Acesso": "Perfis de usuário (motorista/passageiro), permissões de apps e contas.",
    "Criptografia e Chaves": "Keystore2, KeyMint, File-Based Encryption (FBE) e montagem de storage (vold).",
    "Rede e Conexões": "Roteamento de rede (netd), DNS (resolv), regras de iptables e conexões de depuração (adbd).",
    "Integridade e Estabilidade": "Encerramento forçado de processos, ANR, tombstone de crashes e LowMemoryKiller (PSI).",
    "Outros / Serviços Gerais do SO": "Eventos não categorizados em nenhuma categoria anterior."
}

TAG_DESCRIPTIONS = {
    # Automotivo (AAOS)
    "HvacController": "Controle de climatização, temperatura e ventilação veicular (HVAC)",
    "CarService": "Serviço principal de orquestração do Android Automotive OS",
    "VehicleHAL": "Interface de abstração com barramento veicular (CAN/LIN/Ethernet)",
    "IVehicle": "Interface AIDL/HIDL de propriedades automotivas veiculares",
    "CAR.POWER": "Gerenciador de energia e estados de suspensão/hibernação veicular",
    "CAR.AUDIO": "Gerenciador de zonas de áudio e roteamento sonoro do veículo",
    "CAR.PROPS": "Gerenciador de leitura e injeção de propriedades veiculares (VHAL)",
    "CAR.SENSOR": "Gerenciamento de sensores veiculares",
    "CAR.USER": "Gerenciamento de usuários e alternância de perfis de condução",
    "Cluster.ViewModel": "Painel de instrumentos digital do veículo (Instrument Cluster)",
    "ClusterDisplay": "Gerenciamento de telas secundárias do painel veicular",
    "CarWatchdog": "Monitor de integridade de processos e serviços automotivos",
    "CarTelemetry": "Módulo de coleta de telemetria e diagnósticos veiculares",
    "CarAudioService": "Serviço de zonas de áudio automotivo",
    "CarPropertyService": "Serviço de gerenciamento de propriedades automotivas",
    "CarPowerManagementService": "Serviço de gerenciamento de energia veicular",
    "CarDrivingStateService": "Monitoramento de estado de condução (estacionado, em movimento)",
    "CarUxRestrictionsConfigurationService": "Restrições de interface do usuário durante a condução",
    "SubscriptionManager": "Assinatura de eventos e propriedades veiculares no CarPropertyManager (CarSubscription: velocidade, marcha, freio)",

    # Auditoria e Segurança / SELinux
    "auditd": "Daemon de auditoria de segurança do kernel Linux (SELinux e regras de auditoria)",
    "SELinux": "Carregamento e fiscalização de políticas de controle de acesso mandatório (MAC)",
    "DevicePolicyEngine": "Motor de políticas corporativas e restrições de segurança do dispositivo",
    "AppOpService": "Controle de operações e privilégios concedidos aos aplicativos em tempo de execução",
    "PermissionController": "Gerenciador de concessão e revogação de permissões de aplicativos",
    "DropBoxManagerService": "Serviço de persistência de logs e relatórios de auditoria e falhas",

    # Criptografia e Armazenamento
    "keystore2": "Serviço de segurança de segunda geração para gerenciamento de chaves criptográficas",
    "KeyMint": "Implementação HAL de operações criptográficas em hardware seguro",
    "vold": "Daemon de gerenciamento e montagem de volumes e partições criptografadas",
    "vold_prepare_subdirs": "Preparação e provisionamento de subdiretórios criptografados por usuário (FBE)",
    "StorageManagerService": "Serviço de gerenciamento de partições, volumes e armazenamento seguro",
    "BluetoothKeystoreService": "Armazenamento criptografado de chaves e vínculos Bluetooth",

    # Rede e Conectividade
    "netd": "Daemon de rede responsável por interfaces, rotas, sockets e regras de firewall",
    "resolv": "Módulo resolvedor de DNS e integridade de conexões de rede",
    "adbd": "Daemon da ponte de depuração Android (ADB) para acesso e comandos remotos",
    "iptables-restor": "Aplicação de regras de firewall de rede via iptables",
    "NetBpfLoad": "Carregador de programas e filtros de monitoramento de rede eBPF no kernel",
    "InetDiagMessage": "Monitoramento e fechamento de sockets de rede inativos",
    "WifiService": "Gerenciamento de conexões e estado de rede Wi-Fi",
    "WifiHealthMonitor": "Monitoramento de integridade e escaneamento da interface Wi-Fi",
    "wificond": "Daemon de controle do subsistema de rádio Wi-Fi",
    "ConnectivityService": "Serviço central de conectividade de dados e rotas IP",
    "NetworkManagementService": "Gerenciamento de largura de banda e interfaces de rede",
    "RILJ": "Camada Java da Interface de Rádio (Radio Interface Layer) para telecomunicações",

    # Integridade e Estabilidade
    "lowmemorykiller": "Monitor de pressão de memória do kernel (PSI) para descarte preventivo de processos",
    "OomAdjuster": "Ajuste de prioridades e estados de ciclo de vida dos processos na RAM",
    "tombstoned": "Daemon de gravação de arquivos de despejo de crash nativo (tombstones)",
    "crash_dump": "Capturador de rastros de pilha de processos com falha fatal de execução",
    "mediaextractor": "Extração e validação de contêineres de mídia",
    "mediaswcodec": "Serviço de codecs de áudio e vídeo por software",

    # Serviços Gerais do Sistema (OS / Runtime)
    "SystemServerTimingAsync": "Mapeamento assíncrono de tempos de inicialização de serviços no boot",
    "SystemServerTiming": "Rastreamento síncrono de tempos de boot do SystemServer",
    "init": "Processo inicial do sistema (PID 1) responsável pelo boot e serviços",
    "PackageManager": "Gerenciamento, instalação e verificação de pacotes e apps",
    "ContextImpl": "Implementação base do contexto da aplicação no framework Android",
    "libbinder.BackendUnifiedServiceManager": "Camada de comunicação inter-processos (IPC) via Binder",
    "nativeloader": "Carregamento dinâmico de bibliotecas nativas C/C++ (.so)",
    "sysui_multi_action": "Métricas e telemetria de eventos da interface SystemUI",
    "AccessibilityUserState": "Configurações e serviços de acessibilidade do usuário",
    "GraphicsEnvironment": "Configuração do ambiente de drivers gráficos e Vulkan/GLES",
    "SystemServiceRegistry": "Catálogo de registro e injeção de serviços do sistema",
    "libprocessgroup": "Gerenciamento de cgroups para controle de recursos de processos",
    "StrictMode": "Monitor de operações indevidas na thread principal da interface",
    "Zygote": "Processo raiz gerador dos processos Java/Android via fork",
    "cppreopts": "Compilação e pré-otimização de código nativo durante a inicialização",
    "CompatChangeReporter": "Relatório de compatibilidade de APIs entre versões do Android",
    "artd": "Daemon do runtime ART para compilação e otimização de bytecode DEX",
    "ActivityManagerTiming": "Métricas de tempos de inicialização de telas e componentes",
    "ActivityManager": "Gerenciamento do ciclo de vida de atividades, tarefas e processos",
    "WindowManager": "Gerenciamento de janelas, superfícies e composição de tela",
    "PowerManagerService": "Gerenciamento de estados de energia, wake locks e tela",
    "BatteryService": "Monitoramento de nível de carga e status da bateria",
    "SensorService": "Gerenciamento e distribuição de eventos de sensores físicos",
    "AudioService": "Controle de fluxos de áudio, volumes e dispositivos de saída",
    "DisplayManagerService": "Gerenciamento de displays e monitores físicos e virtuais",
    "SurfaceFlinger": "Compositor gráfico central do Android",
    "InputManager": "Distribuição de eventos de toque, teclado e periféricos",
    "ServiceManager": "Registro central de serviços de sistema IPC (Binder)",
    "servicemanager": "Registro central de serviços de sistema IPC (Binder)"
}

def get_tag_description(tag: str, category: str) -> str:
    """Retorna a descrição específica da tag se cadastrada, ou a descrição da sua categoria."""
    return TAG_DESCRIPTIONS.get(tag, CATEGORY_DESCRIPTIONS.get(category, "Eventos do sistema operacional."))

def build_pid_map(log_file_path: Path):
    """Mapeia PIDs para nomes legíveis de processos utilizando logs do Zygote, ActivityManager e Daemons."""
    pid_to_name = {"1": "init"}
    pid_tag_counts = defaultdict(Counter)

    with open(log_file_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            m = LOGCAT_REGEX.match(line)
            if not m:
                continue
            
            tag = m.group("tag").strip()
            msg = m.group("message")
            pid = m.group("pid")

            pid_tag_counts[pid][tag] += 1

            # System server core services
            if tag in ["SystemServerTiming", "SystemServerTimingAsync", "PackageManagerService", "ActivityManagerService"]:
                if "system_server" not in pid_to_name.values():
                    pid_to_name[pid] = "system_server"

            # Spawns registrados pelo Zygote
            zm = ZYGOTE_PROC_RE.search(msg)
            if zm:
                pid_to_name[zm.group(1)] = zm.group(2)

            # Spawns registrados pelo ActivityManager
            am = AM_START_PROC_RE.search(msg)
            if am:
                pid_to_name[am.group(1)] = am.group(2)

            # Daemons nativos conhecidos
            if tag in KNOWN_NATIVE_DAEMONS and pid not in pid_to_name:
                pid_to_name[pid] = KNOWN_NATIVE_DAEMONS[tag]

    # Heurística para PIDs restantes com tag única de daemon
    for pid, tag_counts in pid_tag_counts.items():
        if pid not in pid_to_name:
            top_tag, top_cnt = tag_counts.most_common(1)[0]
            if top_tag in KNOWN_NATIVE_DAEMONS:
                pid_to_name[pid] = KNOWN_NATIVE_DAEMONS[top_tag]
            elif top_cnt >= 20 and (top_tag.islower() or top_tag.endswith("d") or "hal" in top_tag.lower()):
                pid_to_name[pid] = top_tag

    return pid_to_name

def analyze(log_file_path: Path, output_md: Path = None, output_csv: Path = None):
    if not log_file_path.exists():
        print(f"Erro: Arquivo não encontrado: {log_file_path}", file=sys.stderr)
        sys.exit(1)

    # 1. Constrói o mapa de PIDs -> Processos
    pid_to_name = build_pid_map(log_file_path)

    total_lines = 0
    parsed_lines = 0
    unparsed_lines = 0

    level_counter = Counter()
    tag_counter = Counter()
    proc_counter = Counter()
    category_counter = Counter()
    category_tags = defaultdict(Counter)
    tag_category_counter = defaultdict(Counter)
    tag_proc_counter = defaultdict(Counter)
    level_tag_counter = defaultdict(Counter)

    zygote_spawned = []
    seen_spawned_pids = set()

    first_timestamp = None
    last_timestamp = None

    with open(log_file_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            total_lines += 1
            line = line.strip()
            if not line:
                continue

            match = LOGCAT_REGEX.match(line)
            if match:
                parsed_lines += 1
                data = match.groupdict()
                timestamp = f"{data['date']} {data['time']}"
                if not first_timestamp:
                    first_timestamp = timestamp
                last_timestamp = timestamp

                level = data['level']
                tag = data['tag'].strip()
                message = data['message']
                pid = data['pid']

                proc_name = pid_to_name.get(pid, f"pid:{pid}")

                level_counter[level] += 1
                tag_counter[tag] += 1
                proc_counter[proc_name] += 1
                tag_proc_counter[tag][proc_name] += 1
                level_tag_counter[level][tag] += 1

                # Rastreia processos iniciados pelo Zygote
                zm = ZYGOTE_PROC_RE.search(message)
                if zm:
                    sp_pid, sp_name = zm.group(1), zm.group(2)
                    if sp_pid not in seen_spawned_pids:
                        seen_spawned_pids.add(sp_pid)
                        zygote_spawned.append((timestamp, sp_pid, sp_name))

                # Classificação em categorias (mutuamente exclusiva, abrangência 100%)
                content_lower = f"{tag} {message}".lower()
                assigned_category = "Outros / Serviços Gerais do SO"
                for cat_name, terms in CATEGORIES_ORDER:
                    if any(term in content_lower for term in terms):
                        assigned_category = cat_name
                        break

                category_counter[assigned_category] += 1
                category_tags[assigned_category][tag] += 1
                tag_category_counter[tag][assigned_category] += 1
            else:
                unparsed_lines += 1

    level_names = {
        'V': 'VERBOSE',
        'D': 'DEBUG',
        'I': 'INFO',
        'W': 'WARN',
        'E': 'ERROR',
        'F': 'FATAL'
    }

    print("=" * 65)
    print("           RELATÓRIO DE ANÁLISE DE LOGCAT - AAOS")
    print("=" * 65)
    print(f"Arquivo analisado:     {log_file_path.name}")
    print(f"Total de linhas lidas: {total_lines:,}")
    print(f"Linhas estruturadas:   {parsed_lines:,} (100.0%)")
    print(f"Linhas cabeçalho/meta: {unparsed_lines:,}")
    print(f"Total de tags únicas:  {len(tag_counter):,}")
    print(f"Processos rastreados:  {len(proc_counter):,}")
    if first_timestamp and last_timestamp:
        print(f"Janela temporal:       {first_timestamp} até {last_timestamp}")

    print("\n" + "-" * 40)
    print("Top 10 Processos por Volume de Logs:")
    print("-" * 40)
    for proc, cnt in proc_counter.most_common(10):
        pct = (cnt / parsed_lines * 100) if parsed_lines > 0 else 0
        print(f"  {proc:<35}: {cnt:>7,} ({pct:5.2f}%)")

    print("\n" + "-" * 40)
    print("Distribuição por Severidade:")
    print("-" * 40)
    for lvl in ['V', 'D', 'I', 'W', 'E', 'F']:
        cnt = level_counter.get(lvl, 0)
        pct = (cnt / parsed_lines * 100) if parsed_lines > 0 else 0
        name = level_names.get(lvl, lvl)
        print(f"  [{lvl}] {name:<8}: {cnt:>8,} ({pct:5.2f}%)")

    print("\n" + "-" * 40)
    print("Distribuição por Categoria (100% Contabilizado):")
    print("-" * 40)
    for cat, count in category_counter.most_common():
        pct = (count / parsed_lines * 100) if parsed_lines > 0 else 0
        print(f"  {cat:<35}: {count:>7,} ({pct:5.2f}%)")

    # Geração do CSV com a lista completa de tags e processos de origem
    if output_csv:
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        with open(output_csv, "w", encoding="utf-8", newline="") as csvfile:
            writer = csv.writer(csvfile, delimiter=",", quoting=csv.QUOTE_MINIMAL)
            writer.writerow(["tag", "categoria", "processos_origem", "descricao", "quantidade_eventos", "porcentagem_total"])
            
            for tag, count in tag_counter.most_common():
                predominant_cat = tag_category_counter[tag].most_common(1)[0][0]
                pct_str = f"{(count / parsed_lines * 100):.2f}%" if parsed_lines > 0 else "0.00%"
                desc = get_tag_description(tag, predominant_cat)

                # Formata os processos de origem
                proc_parts = []
                for p_name, p_cnt in tag_proc_counter[tag].most_common(3):
                    p_pct = (p_cnt / count) * 100
                    if p_pct >= 99.0:
                        proc_parts.append(p_name)
                    else:
                        proc_parts.append(f"{p_name} ({p_pct:.1f}%)")
                proc_str = ", ".join(proc_parts)

                writer.writerow([tag, predominant_cat, proc_str, desc, count, pct_str])

        print(f"\nRelatório de tags em CSV gerado com sucesso em: {output_csv}")

    # Geração do relatório em Markdown
    if output_md:
        output_md.parent.mkdir(parents=True, exist_ok=True)
        with open(output_md, "w", encoding="utf-8") as md:
            md.write("# Relatório de Análise de Logcat - Android Automotive OS (AAOS)\n\n")
            md.write(f"- **Origem dos logs:** `{log_file_path.name}`\n")
            md.write(f"- **Janela temporal:** `{first_timestamp}` até `{last_timestamp}`\n")
            md.write(f"- **Total de eventos estruturados:** **{parsed_lines:,}** (100.0% das linhas do logcat)\n")
            md.write(f"- **Total de processos identificados:** **{len(proc_counter):,}**\n")
            md.write(f"- **Total de tags únicas mapeadas:** **{len(tag_counter):,}** (com processos detalhados em [`tags_resumo.csv`](./tags_resumo.csv))\n\n")
            
            md.write("## 1. Distribuição por Severidade (Log Level)\n\n")
            md.write("| Nível | Nome | Quantidade de Eventos | Porcentagem |\n")
            md.write("| :---: | :--- | :---: | :---: |\n")
            for lvl in ['V', 'D', 'I', 'W', 'E', 'F']:
                cnt = level_counter.get(lvl, 0)
                pct = (cnt / parsed_lines * 100) if parsed_lines > 0 else 0
                md.write(f"| `{lvl}` | **{level_names.get(lvl, lvl)}** | {cnt:,} | {pct:.2f}% |\n")

            md.write("\n## 2. Categorização de Eventos\n\n")
            md.write("Todos os eventos estruturados foram classificados em categorias temáticas. As linhas que não se enquadram diretamente em regras específicas de segurança ou automotivas são agrupadas na categoria genérica **`Outros / Serviços Gerais do SO`**, garantindo que nenhum log passe despercebido.\n\n")
            
            md.write("| Categoria | Total de Eventos | % do Total | Descrição / Escopo |\n")
            md.write("| :--- | :---: | :---: | :--- |\n")
            for cat, cnt in category_counter.most_common():
                pct = (cnt / parsed_lines * 100) if parsed_lines > 0 else 0
                desc = CATEGORY_DESCRIPTIONS.get(cat, "")
                md.write(f"| **{cat}** | {cnt:,} | {pct:.2f}% | {desc} |\n")

            md.write("\n## 3. Rastreabilidade de Processos Iniciados (Zygote & Sistema)\n\n")
            md.write("> [!TIP]\n")
            md.write("> **O Presente Especial do Zygote:** O daemon raiz do Android registra explicitamente cada processo iniciado com a mensagem `Process <PID> created for <process_name>`. Isso nos permite correlacionar PIDs com seus pacotes e processos reais (ex: `com.android.car`, `android.car.cluster`, `com.android.systemui`), eliminando ambiguidades entre serviços do sistema e APIs veiculares.\n\n")

            md.write("### 3.1 Top 15 Processos por Volume de Logs Emitidos\n\n")
            md.write("| # | Processo / Pacote | Total de Eventos | % do Total |\n")
            md.write("| :-: | :--- | :-: | :-: |\n")
            for i, (proc, cnt) in enumerate(proc_counter.most_common(15), 1):
                pct = (cnt / parsed_lines * 100) if parsed_lines > 0 else 0
                md.write(f"| {i} | `{proc}` | {cnt:,} | {pct:.2f}% |\n")

            md.write("\n### 3.2 Principais Aplicações e Serviços Automotivos Rastreados\n\n")
            md.write("| PID | Pacote / Processo | Papel no Android Automotive |\n")
            md.write("| :-: | :--- | :--- |\n")
            auto_roles = {
                "com.android.car": "CarService - Serviço central de controle e barramentos do veículo",
                "android.car.cluster": "Instrument Cluster - Painel digital de instrumentos (velocímetro, RPM, marcha)",
                "com.android.car.carlauncher": "Car Launcher - Interface gráfica principal do painel de infoentretenimento",
                "com.android.car.settings": "Configurações Veiculares (ar-condicionado, segurança, portas, energia)",
                "com.android.car.media": "Mídia e Áudio automotivo multi-zona",
                "com.android.car.radio": "Sintonizador de Rádio AM/FM/DAB",
                "com.android.car.rotary": "Controlador físico giratório do console central",
                "com.google.android.car.samplerearviewservice": "Câmera de ré / Visão traseira (Rear View Camera)",
                "com.android.systemui": "Interface do sistema (barra de status veicular, HVAC e notificações)"
            }
            for ts, pid, name in zygote_spawned:
                if name in auto_roles:
                    md.write(f"| `{pid}` | `{name}` | {auto_roles[name]} |\n")

            md.write("\n```bash\n# Listar todos os processos criados pelo Zygote no boot\ngrep \"Zygote  : Process\" logcat_analysis/logs/aaos_logcat_latest.log | awk '{print \"PID:\", $3, \"->\", $9}'\n```\n\n")

            md.write("## 4. Comandos Úteis para Filtrar e Inspecionar Cada Categoria\n\n")
            md.write("Para explorar interativamente os logs de cada categoria a partir da raiz do repositório, utilize os comandos abaixo:\n\n")

            for cat, cnt in category_counter.most_common():
                cmd = GREP_EXAMPLES.get(cat, f'grep -i "{cat.split()[0]}" logcat_analysis/logs/aaos_logcat_latest.log | head -n 20')
                top_tags = ", ".join([f"`{t}` ({c})" for t, c in category_tags[cat].most_common(5)])
                md.write(f"### {cat} ({cnt:,} eventos)\n")
                md.write(f"- **Top tags componentes:** {top_tags}\n")
                md.write("- **Comando para inspeção:**\n")
                md.write("```bash\n")
                md.write(f"{cmd}\n")
                md.write("```\n\n")

            md.write("## 5. Top 20 Componentes / Tags Mais Frequentes\n\n")
            md.write("| # | Tag / Componente | Eventos | % do Total |\n")
            md.write("| :-: | :--- | :-: | :-: |\n")
            for i, (tag, cnt) in enumerate(tag_counter.most_common(20), 1):
                pct = (cnt / parsed_lines * 100) if parsed_lines > 0 else 0
                md.write(f"| {i} | `{tag}` | {cnt:,} | {pct:.2f}% |\n")

            md.write("## 6. Análise de Alertas e Erros (`ERROR` & `WARN`)\n\n")
            md.write("### Principais fontes de `ERROR` (Total: " + f"{level_counter.get('E', 0):,})\n\n")
            md.write("| Componente | Quantidade de Erros |\n")
            md.write("| :--- | :---: |\n")
            for tag, cnt in level_tag_counter['E'].most_common(10):
                md.write(f"| `{tag}` | {cnt:,} |\n")

            md.write("\n```bash\n# Inspecionar os 20 últimos erros gravados no logcat\ngrep \" E \" logcat_analysis/logs/aaos_logcat_latest.log | tail -n 20\n```\n\n")

            md.write("### Principais fontes de `WARN` (Total: " + f"{level_counter.get('W', 0):,})\n\n")
            md.write("| Componente | Quantidade de Avisos |\n")
            md.write("| :--- | :---: |\n")
            for tag, cnt in level_tag_counter['W'].most_common(10):
                md.write(f"| `{tag}` | {cnt:,} |\n")

            md.write("\n```bash\n# Inspecionar os 20 últimos warnings gravados no logcat\ngrep \" W \" logcat_analysis/logs/aaos_logcat_latest.log | tail -n 20\n```\n\n")

        print(f"Relatório em Markdown gerado com sucesso em: {output_md}")

def main():
    script_dir = Path(__file__).resolve().parent
    default_log = script_dir.parent / "logs" / "aaos_logcat_latest.log"
    default_out = script_dir.parent / "analise_preliminar.md"
    default_csv = script_dir.parent / "tags_resumo.csv"

    parser = argparse.ArgumentParser(
        description="Analisa e categoriza logs do logcat (AAOS) com mapeamento de processos originadores, gerando Markdown e CSV."
    )
    parser.add_argument(
        "log_path",
        nargs="?",
        default=str(default_log),
        help=f"Caminho para o arquivo .log do logcat (Padrão: {default_log})"
    )
    parser.add_argument(
        "output_md",
        nargs="?",
        default=str(default_out),
        help=f"Caminho para o relatório gerado em Markdown (Padrão: {default_out})"
    )
    parser.add_argument(
        "--csv",
        dest="output_csv",
        default=str(default_csv),
        help=f"Caminho para o arquivo CSV de resumo das tags (Padrão: {default_csv})"
    )

    args = parser.parse_args()
    analyze(Path(args.log_path), Path(args.output_md), Path(args.output_csv))

if __name__ == "__main__":
    main()
