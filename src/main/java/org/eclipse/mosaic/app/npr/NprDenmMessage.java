package org.eclipse.mosaic.app.npr;

import org.eclipse.mosaic.lib.objects.v2x.EncodedPayload;
import org.eclipse.mosaic.lib.objects.v2x.MessageRouting;
import org.eclipse.mosaic.lib.objects.v2x.V2xMessage;

/**
 * Representa a mensagem de aviso de perigo (DENM) enviada pela RSU para informar os veículos sobre a zona de obras
 */
public class NprDenmMessage extends V2xMessage {

    // Constantes para simulação da carga útil (Payload)
    private static final int PAYLOAD_SIZE_BYTES = 100;
    private static final int PROCESSING_LATENCY_MS = 800;

    private final long tempoExpiracao; // Time-To-Live (TTL) da mensagem

    // Construtor da mensagem de alerta
    public NprDenmMessage(MessageRouting routing, long tempoExpiracao) {
        super(routing);
        this.tempoExpiracao = tempoExpiracao;
    }

    public long getTempoExpiracao() { 
        return tempoExpiracao; 
    }

    //Define o payload da mensagem
    @Override
    public EncodedPayload getPayload() {
        return new EncodedPayload(PAYLOAD_SIZE_BYTES, PROCESSING_LATENCY_MS);
    }

    @Override
    public String toString() {
        return "NprDenmMessage{validUntil=" + tempoExpiracao + "}";
    }
}