from dash import html

def loading(id=''):
    return(
        html.Div(
            [
                html.Img(src='/assets/img/svg/amsa.svg'),
                html.Span("Cargando datos")   
            ], id=f'loading_wrapper_{id}', className='loading_wrapper'
        )
    )