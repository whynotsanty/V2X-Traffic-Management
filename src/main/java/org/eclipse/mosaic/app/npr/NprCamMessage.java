package org.eclipse.mosaic.app.npr;

import org.eclipse.mosaic.lib.objects.v2x.V2xMessage;
import org.eclipse.mosaic.lib.objects.v2x.MessageRouting;
import org.eclipse.mosaic.lib.objects.v2x.EncodedPayload;

/**
 * Representa a mensagem de awareness cooperativo (CAM)
 */
public class NprCamMessage extends V2xMessage {

    // Tamanho do payload em bytes, configurado para simular um CAM real
    private static final long CAM_PAYLOAD_SIZE = 50L;

    private final double velocidade; // Velocidade do veículo no instante da transmissão

    // Construtor da mensagem CAM
    public NprCamMessage(MessageRouting routing, double velocidade) {
        super(routing);
        this.velocidade = velocidade;
    }

    public double getVelocidade() { 
        return velocidade; 
    }

    // Retorna o payload codificado da mensagem
    @Override
    public EncodedPayload getPayload() {
        return new EncodedPayload(CAM_PAYLOAD_SIZE);
    }

    @Override
    public String toString() {
        return "NprCamMessage{speed=" + velocidade + " m/s}";
    }
}