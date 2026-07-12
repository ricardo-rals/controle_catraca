javascript
// dashboard/static/dashboard/js/grafico-volume.js
document.addEventListener('DOMContentLoaded', function () {
    // Leitura segura — sem interpolação manual de JSON
    const dados = JSON.parse(document.getElementById('dados-volume').textContent);
    const granularidade = JSON.parse(document.getElementById('granularidade-volume').textContent);

    const labels = dados.map(item => item.periodo);
    const valores = dados.map(item => item.total);

    const ctx = document.getElementById('graficoVolume').getContext('2d');

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Volume',
                data: valores,
                borderColor: '#4f46e5',
                backgroundColor: 'rgba(79, 70, 229, 0.1)',
                fill: true,
                tension: 0.3,
                pointRadius: 3,
            }]
        },
        options: {
            responsive: true,
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            // Valor exato, sem arredondamento
                            return `Volume: ${context.parsed.y}`;
                        }
                    }
                },
                legend: { display: false }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: granularidade === 'dia' ? 'Dia'
                             : granularidade === 'semana' ? 'Semana'
                             : 'Mês'
                    }
                },
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'Total' }
                }
            }
        }
    });
});

