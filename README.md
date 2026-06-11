# Gestão Cooperativa de Tráfego em Zona de Obras com V2X

Este projeto propõe uma arquitetura de controlo cooperativo baseada em comunicações V2X para mitigar os impactos negativos de zonas de obras rodoviárias. O sistema implementa uma infraestrutura inteligente (RSU) que atua como mediadora no tráfego, difundindo recomendações dinâmicas de velocidade aos veículos nas imediações.

A solução foi desenvolvida e validada no ambiente de co-simulação Eclipse MOSAIC, em acoplamento direto com o simulador de tráfego SUMO. 

## 🛠️ Tecnologias e Ferramentas
* **Simulador de Tráfego:** SUMO (Simulation of Urban MObility)
* **Ambiente de Co-Simulação:** Eclipse MOSAIC
* **Pilha Protocolar de Comunicação:** ETSI ITS-G5

## ⚙️ Arquitetura do Sistema e Comunicações

A infraestrutura de rede foi desenhada para operar em cenários de elevada densidade veicular, rejeitando abordagens de flooding cego. 

* **Distance-Based Contention Forwarding (DBCF):** Mecanismo de mitigação de congestionamento de canal que atribui prioridade de retransmissão aos recetores mais distantes da fonte.
* **Directional Geocasting:** Técnica implementada para otimizar o uso do canal rádio, garantindo que veículos fora da zona crítica silenciam a cadeia de propagação.
* **Lógica de Histerese:** A RSU incorpora um sistema condicional de duplo limiar para mitigar a oscilação constante de diretrizes de velocidade.
* **Afunilamento Cinético:** A velocidade recomendada é determinada de forma adaptativa pelo estado do tráfego e modulada pela distância do recetor à zona de obras.

## 🗺️ Cenário de Simulação

* O cenário principal de validação consiste numa rede em formato de grid de Manhattan 4x4.
* A topologia é composta por 3 RSUs, 4 zonas de semáforos e 4 zonas com rotundas.
* A injeção de tráfego estocástico foi gerada via script em Python (randomTrips.py).
* Os testes contemplaram perfis de condução com diferentes taxas de penetração cooperativa (0%, 25%, 50% e 100%).

## 📊 Principais Resultados

A avaliação quantitativa demonstrou que a coordenação Edge em ambientes ITS adversos exige um compromisso entre escoamento máximo e segurança.

* **Absorção de Ondas de Choque:** O sistema reduz de forma contundente os tempos de viagem extremos (percentil 95), comprovando a absorção de ondas de choque.
* **Previsibilidade:** A arquitetura sacrifica a capacidade de escoamento bruto em prol da segurança e da estabilidade do fluxo.
* **Resiliência da Rede:** O algoritmo DBCF permitiu suprimir cerca de 70% do tráfego redundante no canal ITS-G5, anulando o risco de broadcast storms.
* **Estabilização Física:** A extensão máxima das filas de espera (spillback) apresenta clara estabilização nos picos de cooperação veicular.
