# Análise de Logcat no AAOS (Android Automotive OS) para SIEM

Este módulo contém ferramentas e documentação para captura, persistência, categorização e análise estatística dos logs gerados pelo Android Automotive OS (`logcat`).

---

## Estrutura do Módulo

```text
logcat_analysis/
├── README.md                  # Este guia de uso e referência
├── analise_preliminar.md      # Relatório atualizado com métricas e comandos
├── tags_resumo.csv            # Tabela CSV com todas as tags, categorias, descrições e contagens
├── logs/                      # Armazenamento dos arquivos .log brutos
│   ├── aaos_logcat_<TIMESTAMP>.log
│   └── aaos_logcat_latest.log -> (link simbólico para a captura mais recente)
└── scripts/
    ├── save_logcat.sh         # Script Shell (nativo) para persistência dos logs
    └── analyze_logcat.py      # Parser e analisador estatístico com foco em SIEM
```

---

## Guia de Uso Rápido

### 1. Coletar e Salvar o Logcat
Com a VM do Cuttlefish em execução, execute o script de captura:

```bash
./logcat_analysis/scripts/save_logcat.sh
```

**Como funciona o `save_logcat.sh`:**
- Ele localiza automaticamente o diretório da instância Cuttlefish ativa (`/var/tmp/cvd/.../logs/logcat`), que contém todo o histórico desde o primeiro milissegundo de boot.
- Se o arquivo do host não estiver acessível, ele recorre ao `adb logcat -b all -d -v threadtime`.
- Salva o resultado em `logs/aaos_logcat_<DATA_HORA>.log` e atualiza o atalho `logs/aaos_logcat_latest.log`.

Para ver as opções do script:
```bash
./logcat_analysis/scripts/save_logcat.sh --help
```

---

### 2. Executar a Análise Estatística
Para processar o log mais recente e atualizar o relatório em Markdown e a planilha CSV:

```bash
./logcat_analysis/scripts/analyze_logcat.py
```

Ou especificando um arquivo de log, saída em Markdown e CSV customizados:
```bash
./logcat_analysis/scripts/analyze_logcat.py caminho/do/arquivo.log meu_relatorio.md --csv minhas_tags.csv
```

**O que o `analyze_logcat.py` faz:**
- **Distribuição de Severidade:** Mede a proporção de `VERBOSE`, `DEBUG`, `INFO`, `WARN`, `ERROR` e `FATAL`.
- **Top Tags e Erros:** Mapeia os 20 componentes mais ativos e as principais fontes de falha/alerta.
- **Rastreabilidade de Processos:** Mapeia os processos de origem de cada evento e tag a partir dos registros do Zygote, ActivityManager e daemons nativos.
- **Exportação em CSV (`tags_resumo.csv`):** Lista completa de todas as tags únicas com a coluna de **processos de origem**, categorização, descrição funcional, quantidade e porcentagem.
- **Geração de Comandos CLI:** Insere comandos prontos (`grep` / `cat`) no relatório para facilitar consultas rápidas.

---

## Rastreabilidade de Processos: O Presente do Zygote

O log do **Zygote** no Android traz um presente especial para análise de observabilidade e SIEM: sempre que um novo processo de aplicativo ou serviço é inicializado, o Zygote registra explicitamente no logcat uma entrada estruturada:

```text
I Zygote  : Process <PID> created for <nome_do_pacote>
```

### Por que isso é fundamental para SIEM e Segurança?
- **Identificação precisa de PIDs:** Não é necessário adivinhar a origem de um evento no log ou depender de comandos voláteis como `ps` em tempo de execução. O histórico de PIDs fica registrado para auditoria post-mortem.
- **Desambiguação de tags:** Componentes que compartilham nomes genéricos (como o `SubscriptionManager`, que no AAOS pertence a `com.android.car` e `android.car.cluster`, e não a chips telefônicos) têm sua real identidade revelada.
- **Auditoria de processos veiculares:** Permite listar toda a árvore de aplicações automotivas carregadas na inicialização do sistema de infoentretenimento (Car Launcher, Cluster, HVAC, Settings).

Para listar rapidamente todos os processos e pacotes instanciados pelo Zygote:
```bash
grep "Zygote  : Process" logcat_analysis/logs/aaos_logcat_latest.log | awk '{print "PID:", $3, "->", $9}'
```

---

## Categorias Monitoradas

| Categoria | Descrição / Escopo | Palavras-chave de Referência |
| :--- | :--- | :--- |
| **Subssistema Automotivo (AAOS)** | Barramentos veiculares, HVAC, CarService, Vehicle HAL (VHAL), Cluster e telemetria | `car`, `vehicle`, `vhal`, `hvac`, `cluster`, `telemetry`, `watchdog` |
| **Auditoria e SELinux** | Daemon de auditoria do kernel (`auditd`), checagem de AVC denials e políticas SELinux | `auditd`, `audit`, `avc`, `selinux`, `security` |
| **Gestão de Usuários e Acesso** | Perfis de usuário (motorista/passageiro), permissões de apps e contas | `user`, `permission`, `auth`, `account`, `keyguard`, `locksettings` |
| **Criptografia e Chaves** | Keystore2, KeyMint, File-Based Encryption (FBE) e montagem de storage (`vold`) | `keystore`, `keymint`, `vold`, `crypt`, `fbe` |
| **Rede e Conexões** | Roteamento de rede (`netd`), DNS (`resolv`), regras de `iptables` e conexões de depuração (`adbd`) | `netd`, `iptables`, `firewall`, `resolv`, `wificond`, `adbd` |
| **Integridade e Estabilidade** | Encerramento forçado de processos, ANR, tombstone de crashes e LowMemoryKiller (PSI) | `crash`, `tombstone`, `anr`, `sigsegv`, `lowmemorykiller`, `panic` |
| **Outros / Serviços Gerais do SO** | Eventos não categorizados em nenhuma categoria anterior | *Todos os demais eventos do SO* |

---

## Comandos Úteis para Análise Direta no Terminal

Com o link simbólico `logs/aaos_logcat_latest.log`, você pode inspecionar qualquer categoria diretamente:

### Eventos de Segurança e Auditoria (SELinux / AVC)
```bash
grep -E "auditd|avc|selinux" logcat_analysis/logs/aaos_logcat_latest.log | head -n 20
```

### Eventos do Subssistema Automotivo (CarService / VHAL / HVAC)
```bash
grep -E "HvacController|CarService|VehicleHAL|IVehicle" logcat_analysis/logs/aaos_logcat_latest.log | head -n 20
```

### Comandos e Sessões Executadas via ADB Shell
```bash
grep "adbd" logcat_analysis/logs/aaos_logcat_latest.log | grep "shell"
```

### Alertas e Erros Críticos
```bash
grep " E " logcat_analysis/logs/aaos_logcat_latest.log | tail -n 20
```

### Eventos de Criptografia e Chaves (Keystore / Vold)
```bash
grep -E "keystore|keymint|vold|fscrypt" logcat_analysis/logs/aaos_logcat_latest.log | head -n 20
```
