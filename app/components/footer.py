from dash import html

def footer():
    return html.Footer(
        id="footer",
        className='footer light-mode-amsa py-3 mt-auto container-fluid content-wrapper',
        children=[
            html.Div(className='row align-items-center justify-content-center', children=[
                html.Div(className='col-md-auto align-items-center text-center', children=[
                    html.Img(src='assets/img/svg/envelope-paper.svg', className="footer-icon"),
                    html.Small("mail@aminerals.cl"),
                ]),
                html.Div(className='col-md-auto align-items-center text-center', children=[
                    html.Img(src='assets/img/svg/telephone-inbound.svg', className="footer-icon"),
                    html.Small("+56 9 1234 5678"),
                ]),
                html.Div(className='col-md-auto align-items-center text-center', children=[
                    html.Img(src='assets/img/svg/pin-map.svg', className="footer-icon"),
                    html.Small("Team Name"),
                ]),
            ]),
            
            html.Div(className='row align-items-center justify-content-between', children=[
                html.Div(className='col-md-auto align-items-start text-start amsa-sign', children=[
                    html.Img(src="/assets/img/logos/logo-amsa-white.png", alt="amsa-logo-white", className='pb-2 img-fluid mb-auto footer-logo pb-2'),
                    html.P(className='white', children=[
                        html.Small("Av. Apoquindo 4001, Piso 18"),
                        html.Br(),
                        html.Small("Las Condes, Santiago. Chile"),
                        html.Br(),
                        html.Small("Codigo Postal: 7550162"),
                        html.Br(),
                        html.Small("(56-2) 2798 7000")
                    ])
                ]),
            ]),
        ]
    )
