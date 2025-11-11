from http import HTTPStatus


def test_404(client):
    response = client.get('/unexpected')
    assert response.status_code == HTTPStatus.NOT_FOUND, (
        'При обращении к несуществующей странице должна вернуться ошибка 404.'
    )
    assert (
        ('If you entered the URL manually please check your spelling and try '
         'again.') not in response.data.decode('utf-8')
    ), (
        'Убедитесь, что в проекте реализован и подключен собственный шаблон '
        'для отображения страницы с ошибкой 404.'
    )
