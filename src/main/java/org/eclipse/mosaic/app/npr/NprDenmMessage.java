package org.eclipse.mosaic.app.npr;

import org.eclipse.mosaic.lib.geo.GeoPoint;
import org.eclipse.mosaic.lib.objects.v2x.EncodedPayload;
import org.eclipse.mosaic.lib.objects.v2x.MessageRouting;
import org.eclipse.mosaic.lib.objects.v2x.V2xMessage;

/**
 * Representa a mensagem de aviso de perigo (DENM) enviada pela RSU para informar os veículos sobre a zona de obras.
 * Para além do TTL, transporta a recomendação adaptativa de velocidade e a posição da obra/RSU,
 * permitindo aos veículos calcular distâncias ao referencial correto (a obra) e aplicar a velocidade recomendada.
 */
public class NprDenmMessage extends V2xMessage {

    // Constantes para simulação da carga útil (Payload)
    private static final int PAYLOAD_SIZE_BYTES = 100;
    private static final int PROCESSING_LATENCY_MS = 800;

    private final long tempoExpiracao;             // Time-To-Live (TTL) da mensagem
    private final double velocidadeRecomendada;    // Velocidade recomendada pela RSU (m/s)
    private final GeoPoint posicaoObra;            // Posição da obra/RSU (referencial do funil)

    // Construtor da mensagem de alerta
    public NprDenmMessage(MessageRouting routing, long tempoExpiracao,
                          double velocidadeRecomendada, GeoPoint posicaoObra) {
        super(routing);
        this.tempoExpiracao = tempoExpiracao;
        this.velocidadeRecomendada = velocidadeRecomendada;
        this.posicaoObra = posicaoObra;
    }

    public long getTempoExpiracao() {
        return tempoExpiracao;
    }

    // Velocidade recomendada pela RSU em m/s (resultado da política adaptativa)
    public double getVelocidadeRecomendada() {
        return velocidadeRecomendada;
    }

    // Posição da obra/RSU; referencial usado pelos veículos para o funil de velocidade
    public GeoPoint getPosicaoObra() {
        return posicaoObra;
    }

    //Define o payload da mensagem
    @Override
    public EncodedPayload getPayload() {
        return new EncodedPayload(PAYLOAD_SIZE_BYTES, PROCESSING_LATENCY_MS);
    }

    @Override
    public String toString() {
        return "NprDenmMessage{validUntil=" + tempoExpiracao
                + ", velocidadeRecomendada=" + velocidadeRecomendada + " m/s"
                + ", posicaoObra=" + posicaoObra + "}";
    }
}
