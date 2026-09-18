# Android Automotive OS (AAOS) no Cuttlefish

Este repositório contém os scripts de automação e a documentação completa para subir o **Android Automotive OS (AAOS)** localmente no seu computador Linux (Ubuntu) utilizando o **Cuttlefish Virtual Device (CVD)** com builds contínuas (**nightly/CI build** da AOSP).

Além disso, inclui o roadmap detalhado para a evolução do projeto em direção a hardware embarcado (**Raspberry Pi 4 e 5**) no arquivo [`ROADMAP_RASPBERRY_PI.md`](./ROADMAP_RASPBERRY_PI.md).

---

## Sumário
1. [Visão Geral](#visão-geral)
2. [Pré-requisitos](#pré-requisitos)
3. [Passo a Passo Rápido](#passo-a-passo-rápido)
4. [Acesso Visual via WebRTC](#acesso-visual-via-webrtc)
5. [Depuração e Desenvolvimento com ADB](#depuração-e-desenvolvimento-com-adb)
6. [Simulação do Veículo (VHAL e CarService)](#simulação-do-veículo-vhal-e-carservice)
7. [Scripts Disponíveis](#scripts-disponíveis)
8. [Solução de Problemas (Troubleshooting)](#solução-de-problemas-troubleshooting)

---

## Visão Geral

O **Cuttlefish** é o emulador virtual de referência mantido diretamente pelo Google no AOSP. Diferente de emuladores convencionais, o Cuttlefish executa Android sobre virtualização KVM nativa com aceleração de hardware (virtio-gpu, virtio-input, virtio-net, virtio-snd), permitindo reproduzir com altíssima fidelidade o comportamento de um sistema embarcado automotivo real.

O target **`aosp_cf_x86_64_auto`** inclui a pilha completa do Android Automotive:
- **CarService**: Gerenciamento de usuários veiculares, zonas de áudio, restrições de condução (*driving state*) e gerenciamento de energia veicular.
- **Vehicle HAL (VHAL)**: Camada de abstração que faz a ponte entre os barramentos do veículo (ex: CAN-bus) e o Android.
- **Car Launcher**: Interface de usuário otimizada para painel automotivo (HVAC, mídia, navegação, notificações veiculares).

---

## Pré-requisitos

1. **Sistema Operacional:** Linux x86_64 (Ubuntu 22.04 LTS ou 24.04 LTS recomendado).
2. **Suporte a Virtualização (KVM):**
   - Processador Intel (com VT-x habilitado) ou AMD (com AMD-V / SVM habilitado na BIOS/UEFI).
   - `/dev/kvm` disponível no sistema.
3. **Espaço em Disco:** Mínimo de 15 a 20 GB livres para as imagens do sistema e arquivos de runtime.
4. **Memória RAM:** Mínimo de 8 GB (recomendado 16 GB ou mais).

---

## Passo a Passo Rápido

### Passo 1: Configurar o Host (uma única vez)
Execute o script de configuração como administrador (`sudo`) para adicionar o repositório oficial de artefatos do Google, instalar os pacotes `cuttlefish-base` e `cuttlefish-user`, e adicionar seu usuário aos grupos `kvm`, `cvdnetwork` e `render`:

```bash
sudo ./scripts/setup_host.sh
```

### Passo 2: Aplicar Permissões de Grupo
Após a execução do script, para aplicar as novas permissões de grupo sem precisar reiniciar o computador:

```bash
newgrp kvm
```
*(Se preferir, você também pode reiniciar a máquina para carregar completamente todas as interfaces de rede virtuais e regras udev).*

### Passo 3: Baixar a Nightly Build do AAOS
Execute o script de download dos artefatos mais recentes do target automotivo:

```bash
./scripts/fetch_aaos.sh
```
> O script fará o download da última build bem-sucedida da branch `aosp-main` para o target `aosp_cf_x86_64_auto-trunk_staging-userdebug` (ou `aosp_cf_x86_64_auto-userdebug`). O tamanho total é de aproximadamente ~3 a 5 GB.

### Passo 4: Iniciar o Android Automotive
Inicie a máquina virtual do Cuttlefish:

```bash
./scripts/start_aaos.sh
```

O Cuttlefish subirá em background com tela de alta resolução automotiva (`1920x1080`) e servidor WebRTC ativo.

### Passo 5: Parar o Cuttlefish
Quando terminar os testes, finalize a instância com:

```bash
./scripts/stop_aaos.sh
```

---

## Acesso Visual via WebRTC

O Cuttlefish disponibiliza uma interface web interativa completa através do protocolo WebRTC.

1. Abra o navegador (Google Chrome ou Chromium recomendado) em:
   ```
   https://localhost:8443
   ```
2. O navegador exibirá um aviso de certificado SSL autoassinado (`Sua conexão não é privada`). Clique em **Avançado** e depois em **Prosseguir para localhost**.
3. Você verá o display central do Android Automotive com:
   - Suporte a mouse e touch direto.
   - Teclado do host.
   - Transmissão de áudio do sistema.
   - Painel lateral com botões de volume, power e rotação.

---

## Depuração e Desenvolvimento com ADB

O Cuttlefish conecta-se automaticamente ao daemon do ADB local.

### Verificar conexão
```bash
adb devices
```
*Saída esperada: `127.0.0.1:6520 device`*

### Verificar se o Android terminou a inicialização
```bash
adb shell getprop sys.boot_completed
```
*(Retorna `1` quando o sistema estiver pronto).*

### Acessar o Shell com permissões de Root
Como a build utilizada é `userdebug`, o root está disponível imediatamente:
```bash
adb root
adb shell
```

### Instalar Aplicativos Automotivos (APKs)
```bash
adb install caminho/para/seu_app_automotive.apk
```

---

## Simulação do Veículo (VHAL e CarService)

Uma das maiores vantagens do Android Automotive no Cuttlefish é a capacidade de injetar e simular dados dos sensores veiculares através do `CarService`.

### 1. Inspecionar o CarService
```bash
adb shell dumpsys car_service
```

### 2. Simular Velocidade do Veículo (`PERF_VEHICLE_SPEED`)
A propriedade `PERF_VEHICLE_SPEED` tem ID `291504647` (em m/s).
Para simular o carro a **72 km/h** (20 m/s):
```bash
adb shell cmd car_service inject-vhal-event 291504647 20.0
```

Para zerar a velocidade (carro parado):
```bash
adb shell cmd car_service inject-vhal-event 291504647 0.0
```

### 3. Simular Troca de Marcha (`GEAR_SELECTION`)
A propriedade `GEAR_SELECTION` tem ID `289408000`:
- **Park (P):** `4`
- **Reverse (R):** `8`
- **Neutral (N):** `1`
- **Drive (D):** `2`

Exemplo para engatar **Drive**:
```bash
adb shell cmd car_service inject-vhal-event 289408000 2
```

Exemplo para engatar **Reverse**:
```bash
adb shell cmd car_service inject-vhal-event 289408000 8
```

### 4. Simular Nível de Bateria / Combustível (`EV_BATTERY_LEVEL` ou `FUEL_LEVEL`)
- Simular nível de combustível (mL) ou porcentagem conforme a configuração do HAL:
```bash
adb shell cmd car_service inject-vhal-event 291504903 85.0
```

### 5. Simular Ar-Condicionado / Climatização (HVAC)
- Ajustar temperatura da cabine do motorista (zona 1):
```bash
adb shell cmd car_service inject-vhal-event 358614275 22.0 -z 1
```

---

## Scripts Disponíveis

| Script | Descrição |
|---|---|
| `scripts/setup_host.sh` | Instala pacotes oficiais Cuttlefish, repositório APT e configura grupos `kvm`, `cvdnetwork`, `render`. |
| `scripts/fetch_aaos.sh` | Baixa a versão nightly mais recente dos artefatos do AAOS para Cuttlefish via `cvd fetch`. |
| `scripts/start_aaos.sh` | Inicia o Cuttlefish com parâmetros de tela automotiva widescreen e WebRTC habilitado. |
| `scripts/stop_aaos.sh` | Finaliza com segurança as instâncias ativas do Cuttlefish. |
| `logcat_analysis/scripts/save_logcat.sh` | Persiste todo o logcat do AAOS (Cuttlefish/ADB) em arquivo `.log`. |
| `logcat_analysis/scripts/analyze_logcat.py` | Analisador estatístico de logcat voltado para SIEM e observabilidade. |

> Para mais detalhes sobre análise de logs e segurança, consulte o [**Guia do Módulo de Análise de Logcat**](./logcat_analysis/README.md).

---

## Solução de Problemas (Troubleshooting)

### 1. `Permission denied: /dev/kvm`
- **Causa:** O usuário atual não tem permissão no grupo `kvm`.
- **Solução:** Execute `newgrp kvm` no terminal ou reinicie a sessão do usuário. Verifique com `id` se o grupo `kvm` está presente.

### 2. Porta 8443 em uso
- Se você já tiver outro serviço escutando na porta 8443, configure uma porta alternativa ao iniciar o Cuttlefish:
  ```bash
  cvd start --webrtc_assets_dir=... --webrtc_tcp_port=8444
  ```

### 3. Falha de download com "Rate limit exceeded"
- O script `fetch_aaos.sh` utiliza a ferramenta oficial `cvd fetch`, que gerencia requisições autenticadas e downloads com integridade via Google Storage da Android CI. Se a branch `aosp-main` estiver instável, você pode utilizar a branch de release:
  ```bash
  BRANCH=aosp-android-latest-release TARGET=aosp_cf_x86_64_auto-userdebug ./scripts/fetch_aaos.sh
  ```

### 4. Onde encontrar os logs do emulador?
Os logs detalhados ficam disponíveis no diretório de artefatos:
```bash
tail -f artifacts/cuttlefish_runtime/launcher.log
tail -f artifacts/cuttlefish_runtime/kernel.log
```

---

## Próximos Passos

Para prosseguir com a implementação do Android Automotive OS em hardware físico, consulte o nosso guia arquitetural e técnico:
👉 [**Roadmap para Raspberry Pi (4 e 5)**](file:///home/luciano/Documents/antigravity/hopeful-kepler/ROADMAP_RASPBERRY_PI.md)
