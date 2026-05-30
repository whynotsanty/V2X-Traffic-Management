package org.eclipse.mosaic.app.npr;

import java.awt.Color;
import org.eclipse.mosaic.fed.application.ambassador.simulation.VehicleParameters;
import org.eclipse.mosaic.fed.application.app.AbstractApplication;
import org.eclipse.mosaic.fed.application.app.api.VehicleApplication;
import org.eclipse.mosaic.fed.application.app.api.os.VehicleOperatingSystem;
import org.eclipse.mosaic.lib.objects.vehicle.VehicleData;
import org.eclipse.mosaic.lib.objects.v2x.V2xMessage;
import org.eclipse.mosaic.lib.util.scheduling.Event;
import org.eclipse.mosaic.fed.application.ambassador.simulation.communication.AdHocModuleConfiguration;
import org.eclipse.mosaic.fed.application.app.api.CommunicationApplication;
import org.eclipse.mosaic.fed.application.ambassador.simulation.communication.ReceivedV2xMessage;
import org.eclipse.mosaic.fed.application.ambassador.simulation.communication.ReceivedAcknowledgement;
import org.eclipse.mosaic.fed.application.ambassador.simulation.communication.CamBuilder;
import org.eclipse.mosaic.interactions.communication.V2xMessageTransmission;
import org.eclipse.mosaic.lib.enums.AdHocChannel;

/**
 * Aplicação Veicular para Gestão Cooperativa em Zona de Obras
 * Implementa a pilha V2X (ITS-G5) para processamento de recomendações dinâmicas de velocidade (Opção A) e disseminação multi-hop com mitigação de broadcast storms
 */
public class NprVehicleApp extends AbstractApplication<VehicleOperatingSystem> implements VehicleApplication, CommunicationApplication {

    public enum Personalidade {
        COOPERANTE,
        PADRAO,
        POUCO_COOPERANTE,
        NAO_COOPERANTE
    }

    // Parâmetros de Comportamento e Navegação
    private Personalidade minhaPersonalidade;
    private int zonaDecidida = 0;      
    private boolean decidiuObedecer = false; 
    private double ultimaDistancia = -1; 

    // --- Parâmetros de Rede ITS-G5 ---
    private final long INTERVALO_CAM = 1000000000L; 
    private long proximoCamTempo = 0; 
    private final double RADIO_RANGE = 140.0; 
    private final long T_MAX_ESPERA = 100000000L; 
    
    // Variáveis de Controlo de Retransmissão (Histerese/Supressão)
    private boolean jaRetransmitiu = false;
    private boolean aEsperaDeRetransmitir = false;
    private long tempoAgendadoParaRetransmitir = 0;
    private NprDenmMessage mensagemGuardada = null;

    // Coletores de Métricas
    private MetricsCollector metricsCollector = MetricsCollector.getInstance();
    private long tempoInicio = 0;
    private double velocidadeAcumulada = 0.0;
    private int contadorAmostraVelocidade = 0;

    @Override
    public void onStartup() {
        getOs().getAdHocModule().enable(new AdHocModuleConfiguration()
                .addRadio()
                .channel(AdHocChannel.CCH)
                .power(50)
                .distance((int) RADIO_RANGE)
                .create()
        );

        atribuirPersonalidade();
        pintarCarro();

        System.out.println(String.format("[START] Veículo: %-8s | Personalidade: %-16s | Rádio: %s", 
            getOs().getId(), minhaPersonalidade.name(), getOs().getAdHocModule().isEnabled() ? "OK" : "ERRO"));
        getLog().debugSimTime(this,"CAM INICIADA");

        tempoInicio = getOs().getSimulationTime();
        proximoCamTempo = getOs().getSimulationTime() + INTERVALO_CAM;
        getOs().getEventManager().addEvent(proximoCamTempo, this);
    }

    @Override
    public void processEvent(Event event) throws Exception {
        long tempoAtual = getOs().getSimulationTime();

        // Processamento da transmissão periódica (CAM)
        if (tempoAtual >= proximoCamTempo) {
            double velocidadeAtual = getOs().getVehicleData().getSpeed();

            if (velocidadeAtual >= 0) {
                velocidadeAcumulada += velocidadeAtual;
                contadorAmostraVelocidade++;
            }

            org.eclipse.mosaic.lib.objects.v2x.MessageRouting camRouting = getOs().getAdHocModule().createMessageRouting().topoBroadCast(1);
            getOs().getAdHocModule().sendV2xMessage(new NprCamMessage(camRouting, velocidadeAtual));

            proximoCamTempo = tempoAtual + INTERVALO_CAM;
            getOs().getEventManager().addEvent(proximoCamTempo, this);
        }

        // Execução da retransmissão DENM assíncrona
        if (aEsperaDeRetransmitir && tempoAtual >= tempoAgendadoParaRetransmitir) {
            org.eclipse.mosaic.lib.objects.v2x.MessageRouting routing = getOs().getAdHocModule().createMessageRouting().topoBroadCast(1);
            // Preserva a recomendação de velocidade e a posição da obra originais ao retransmitir.
            NprDenmMessage msgRetransmitida = new NprDenmMessage(routing,
                    mensagemGuardada.getTempoExpiracao(),
                    mensagemGuardada.getVelocidadeRecomendada(),
                    mensagemGuardada.getPosicaoObra());

            getOs().getAdHocModule().sendV2xMessage(msgRetransmitida);
            aEsperaDeRetransmitir = false;
            jaRetransmitiu = true;
            metricsCollector.recordRetransmission();

            System.out.println(String.format("%-8s RETRANSMITIU o alerta para trás (Multi-Hop)!", getOs().getId()));
        }
    }

    // Motor de decisão V2X mediante receção de mensagens
    @Override
    public void onMessageReceived(ReceivedV2xMessage receivedV2xMessage) {
        V2xMessage msg = receivedV2xMessage.getMessage();
        
        if (msg instanceof NprDenmMessage) {
            NprDenmMessage denm = (NprDenmMessage) msg;
            
            if (getOs().getSimulationTime() > denm.getTempoExpiracao()) {
                return;
            }

            // DENM válido recebido.
            metricsCollector.recordDenmReceived();

            org.eclipse.mosaic.lib.geo.GeoPoint minhaPos = getOs().getNavigationModule().getCurrentPosition();

            // Referencial do funil = posição da OBRA (transportada no DENM), não o emissor.
            org.eclipse.mosaic.lib.geo.GeoPoint posicaoObra = denm.getPosicaoObra();
            double distancia = minhaPos.distanceTo(posicaoObra);

            // Distância ao emissor: usada apenas no algoritmo multi-hop (back-off) e nos logs.
            org.eclipse.mosaic.lib.geo.GeoPoint emissorPos = msg.getRouting().getSource().getSourcePosition();
            double distanciaEmissor = minhaPos.distanceTo(emissorPos);
            String nomeEmissor = msg.getRouting().getSource().getSourceName();

            // Velocidade recomendada pela RSU (m/s) — base para a velocidade-alvo modulada por zona.
            double velRecomendada = denm.getVelocidadeRecomendada();

            // Ignorar alertas se o veículo já ultrapassou a obra (distância à obra a aumentar)
            if (ultimaDistancia != -1.0 && distancia > ultimaDistancia) {
                if (decidiuObedecer) {
                    getOs().changeSpeedWithPleasantAcceleration(19.44); // 70 km/h (Retoma velocidade máxima)
                    System.out.println(String.format("%-8s Já passou a obra! Retomando velocidade normal. (Dist: %.1fm)", getOs().getId(), distancia));
                    decidiuObedecer = false;
                    zonaDecidida = 0;
                }
                ultimaDistancia = distancia;
                return;
            }
            ultimaDistancia = distancia;

            // Mecanismo de Supressão e Agendamento (back-off por distância ao EMISSOR)
            if (aEsperaDeRetransmitir) {
                aEsperaDeRetransmitir = false;
                jaRetransmitiu = true;
                metricsCollector.recordSuppression();
                System.out.println(String.format("%-8s SUPRIMIU envio (ouviu o alerta de %s).", getOs().getId(), nomeEmissor));
            } else if (!jaRetransmitiu) {
                double d = Math.min(distanciaEmissor, RADIO_RANGE);
                long tEspera = (long) (T_MAX_ESPERA * (1.0 - (d / RADIO_RANGE)));
                tEspera += (long) (getRandom().nextDouble() * 10000000L); // Aleatorização para evitar colisões de retransmissão

                tempoAgendadoParaRetransmitir = getOs().getSimulationTime() + tEspera;
                mensagemGuardada = denm;
                aEsperaDeRetransmitir = true;

                getOs().getEventManager().addEvent(tempoAgendadoParaRetransmitir, this);
                System.out.println(String.format("%-8s AGENDOU retransmissão para %.1f ms (Dist emissor: %.1fm)", getOs().getId(), tEspera / 1000000.0, distanciaEmissor));
            }

            // Mapeamento espacial do funil de velocidade (distância à OBRA)
            int zonaAtual;
            if      (distancia > 500) zonaAtual = 1;
            else if (distancia > 200) zonaAtual = 2;
            else                      zonaAtual = 3;

            // Avaliação estocástica de adoção tecnológica
            if (zonaAtual > zonaDecidida) {
                decidiuObedecer = (getRandom().nextDouble() < getProbabilidade());
                zonaDecidida = zonaAtual;
                System.out.println(String.format("%-8s [%-16s] ZONA %d → %s", getOs().getId(), minhaPersonalidade.name(), zonaAtual, decidiuObedecer ? "OBEDECE" : "IGNORA"));
            }

            // Velocidade-alvo = recomendação da RSU modulada pela zona de distância à obra.
            // Longe: respeita a recomendação; muito perto: aperta para no máximo 30 km/h.
            if (decidiuObedecer && zonaAtual > 0) {
                final double LIMITE_PERTO_MS = 30.0 / 3.6; // 30 km/h
                double velocidadeAlvo = (zonaAtual == 3) ? Math.min(velRecomendada, LIMITE_PERTO_MS)
                                                         : velRecomendada;

                if (minhaPersonalidade == Personalidade.COOPERANTE) {
                    getOs().changeSpeedWithPleasantAcceleration(velocidadeAlvo);
                    System.out.println(String.format("%-8s [COOPERANTE] Zona %d → %.0f km/h (SUAVE)", getOs().getId(), zonaAtual, velocidadeAlvo * 3.6));
                } else if (minhaPersonalidade == Personalidade.PADRAO) {
                    getOs().changeSpeedWithInterval(velocidadeAlvo, 5000000000L);
                    System.out.println(String.format("%-8s [PADRAO] Zona %d → %.0f km/h", getOs().getId(), zonaAtual, velocidadeAlvo * 3.6));
                } else if (minhaPersonalidade == Personalidade.POUCO_COOPERANTE) {
                    getOs().changeSpeedWithInterval(velocidadeAlvo, 2000000000L);
                    System.out.println(String.format("%-8s [POUCO_COOP] Zona %d → %.0f km/h (BRUSCO)", getOs().getId(), zonaAtual, velocidadeAlvo * 3.6));
                }
            }
        }
    }

    @Override
    public void onAcknowledgementReceived(ReceivedAcknowledgement acknowledgedMessage) {}

    @Override
    public void onCamBuilding(CamBuilder camBuilder) {}

    @Override
    public void onMessageTransmitted(V2xMessageTransmission v2xMessageTransmission) {}

    // Define o perfil de adoção às recomendações da infraestrutura
    private double getProbabilidade() {
        switch (minhaPersonalidade) {
            case COOPERANTE:       return 1.0; 
            case PADRAO:           return 0.5; 
            case POUCO_COOPERANTE: return 0.25; 
            default:               return 0.0; 
        }
    }

    
    // Distribuição global de perfis de condução no cenário ativo
    private void atribuirPersonalidade() { 
        double sorteio = getRandom().nextDouble();
        
        // Tráfego Recetivo, corresponde ao Teste 3: 50% Coop | 50% Padrão
        if (sorteio < 0.50) { 
            minhaPersonalidade = Personalidade.COOPERANTE;
        } else { 
            minhaPersonalidade = Personalidade.PADRAO;
        } 
    }

    private void pintarCarro() {
        VehicleParameters.VehicleParametersChangeRequest mudarCor = getOs().requestVehicleParametersUpdate();
        if (minhaPersonalidade == Personalidade.COOPERANTE) {
            mudarCor.changeColor(Color.GREEN);
        } else if (minhaPersonalidade == Personalidade.PADRAO) {
            mudarCor.changeColor(Color.BLUE);
        } else if (minhaPersonalidade == Personalidade.POUCO_COOPERANTE) {
            mudarCor.changeColor(Color.MAGENTA);
        } else {
            mudarCor.changeColor(Color.RED);
        }
        getOs().applyVehicleParametersChange(mudarCor);
    }

    @Override
    public void onShutdown() {
        System.out.println(String.format("\n[ STOP] Veículo: %-8s | Desligado.", getOs().getId()));

        long tempoFim = getOs().getSimulationTime();
        double tripDuration = (tempoFim - tempoInicio) / 1e9; 
        double avgSpeed = contadorAmostraVelocidade > 0 ? velocidadeAcumulada / contadorAmostraVelocidade : 0;
        
        // Estimações para a grelha de avaliação
        double routeLength = avgSpeed * tripDuration; 
        double estimatedCo2 = routeLength * 0.1; 
        double estimatedFuel = routeLength * 0.05; 

        metricsCollector.recordVehicleTrip(getOs().getId(), tripDuration, avgSpeed, estimatedCo2, estimatedFuel, routeLength);
    }

    @Override
    public void onVehicleUpdated(VehicleData previousVehicleData, VehicleData updatedVehicleData) {}
}