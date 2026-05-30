package org.eclipse.mosaic.app.npr;

import org.eclipse.mosaic.fed.application.app.AbstractApplication;
import org.eclipse.mosaic.fed.application.app.api.os.RoadSideUnitOperatingSystem;
import org.eclipse.mosaic.fed.application.app.api.CommunicationApplication;
import org.eclipse.mosaic.fed.application.ambassador.simulation.communication.ReceivedV2xMessage;
import org.eclipse.mosaic.fed.application.ambassador.simulation.communication.ReceivedAcknowledgement;
import org.eclipse.mosaic.fed.application.ambassador.simulation.communication.AdHocModuleConfiguration;
import org.eclipse.mosaic.fed.application.ambassador.simulation.communication.CamBuilder;
import org.eclipse.mosaic.interactions.communication.V2xMessageTransmission;
import org.eclipse.mosaic.lib.util.scheduling.Event;
import org.eclipse.mosaic.lib.enums.AdHocChannel;
import java.util.HashMap;
import java.util.Map;

/**
 * Aplicação de Infraestrutura (RSU) para Gestão de Tráfego
 * Implementa uma política de controlo, baseada na densidade de tráfego recolhida via mensagens CAM
 */
public class NprRsuApp extends AbstractApplication<RoadSideUnitOperatingSystem> implements CommunicationApplication {

    // Limiares para o mecanismo de histerese 
    private static final int LIMIAR_ALTO = 10; // Trigger para início do aviso
    private static final int LIMIAR_BAIXO = 4; // Reset do aviso (prevenção de oscilação)
    
    private boolean avisoAtivo = false; 
    private final Map<String, Double> velocidadesVeiculos = new HashMap<>();

    private MetricsCollector metricsCollector = MetricsCollector.getInstance();

    @Override
    public void onStartup() {
        getOs().getAdHocModule().enable(new AdHocModuleConfiguration()
                .addRadio()
                .channel(AdHocChannel.CCH)
                .power(50)
                .distance(140)
                .create()
        );
        
        System.out.println("[INFO] RSU " + getOs().getId() + " inicializada para controlo de tráfego.");
        // Agendamento do ciclo de controlo da RSU (2 segundos)
        getOs().getEventManager().addEvent(getOs().getSimulationTime() + 2000000000L, this); 
    }

    // Processa a receção de mensagens CAM dos veículos
  
    @Override
    public void onMessageReceived(ReceivedV2xMessage receivedV2xMessage) {
        if (!(receivedV2xMessage.getMessage() instanceof NprCamMessage)) {
            return;
        }
        NprCamMessage cam = (NprCamMessage) receivedV2xMessage.getMessage();
        String vehicleId = cam.getRouting().getSource().getSourceName();
        
        velocidadesVeiculos.put(vehicleId, cam.getVelocidade());
        metricsCollector.recordCamReceived();
    }

    // Monitorização de densidade e broadcast de DENMs

    @Override
    public void processEvent(Event event) throws Exception {
        int densidadeAtual = velocidadesVeiculos.size();
        metricsCollector.recordQueueLength(densidadeAtual);

        double velMediaKmH = 0;
        if (densidadeAtual > 0) {
            velMediaKmH = velocidadesVeiculos.values().stream()
                    .mapToDouble(Double::doubleValue)
                    .average()
                    .orElse(0) * 3.6;
        }

        metricsCollector.recordBottleneckSpeed(velMediaKmH);

        // Lógica de Controlo com Histerese Dupla
        if (!avisoAtivo && densidadeAtual >= LIMIAR_ALTO && velMediaKmH < 40.0) {
            avisoAtivo = true;
            System.out.println(String.format("[CONTROLO] Congestionamento detetado. Estado: ATIVO."));
        } 
        else if (avisoAtivo && (densidadeAtual <= LIMIAR_BAIXO || velMediaKmH > 60.0)) {
            avisoAtivo = false;
            System.out.println(String.format("[CONTROLO] Fluxo regularizado. Estado: INATIVO."));
        }

        if (avisoAtivo) {
            metricsCollector.recordAlertTriggered();
            enviarAvisoObras();
        }

        // Limpeza do buffer de estado e reagendamento do ciclo
        velocidadesVeiculos.clear();
        getOs().getEventManager().addEvent(getOs().getSimulationTime() + 2000000000L, this);
    }

    // Disseminação de mensagens DENM 
    private void enviarAvisoObras() {
        try {
            org.eclipse.mosaic.lib.objects.v2x.MessageRouting routing = getOs().getAdHocModule()
                    .createMessageRouting()
                    .topoBroadCast(1);
            
            long tempoDeValidade = getOs().getSimulationTime() + 5000000000L; 
            NprDenmMessage aviso = new NprDenmMessage(routing, tempoDeValidade);
            
            getOs().getAdHocModule().sendV2xMessage(aviso);
        } catch (Exception e) {
            getLog().error("Erro na disseminação DENM: " + e.getMessage());
        }
    }

    @Override
    public void onAcknowledgementReceived(ReceivedAcknowledgement acknowledgedMessage) {}

    @Override
    public void onCamBuilding(CamBuilder camBuilder) {}

    @Override
    public void onMessageTransmitted(V2xMessageTransmission v2xMessageTransmission) {}

    @Override
    public void onShutdown() {
        System.out.println("[INFO] RSU " + getOs().getId() + " finalizou operações.");
        
        // Gerar relatório final de métricas
        metricsCollector.generateReport();
        System.out.println("[MÉTRICAS] Relatório gerado em: /home/netsim/tpnpr/metrics_from_wrapper.json");
    }
}