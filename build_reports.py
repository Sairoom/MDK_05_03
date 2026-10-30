from pathlib import Path
import json, shutil
from datetime import datetime, timezone, timedelta
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.section import WD_SECTION_START
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT=Path(__file__).resolve().parent
E=ROOT/'evidence'
RESULT=json.loads((E/'results.json').read_text('utf-8'))
HTTP=json.loads((E/'http.json').read_text('utf-8'))
R={r['id']:r for r in RESULT['results']}
DATE=datetime.fromisoformat(RESULT['executedAt'].replace('Z','+00:00')).astimezone(timezone(timedelta(hours=3))).strftime('%d.%m.%Y %H:%M МСК')
ENV=f"Дата проверки: {DATE}. Окружение: Windows x64, Chromium {RESULT['browser']}, headless, окно 1280 × 900. Объект: https://www.saucedemo.com/."
OUT=ROOT/'reports';OUT.mkdir(exist_ok=True)

class Report:
    def __init__(self,number,topic):
        self.stem=f'practice_{number}'
        self.doc=Document(ROOT/'templates'/'title.docx')
        p=self.doc.paragraphs[2]
        # Preserve the supplied title page, changing only the Lesson XX topic.
        p.runs[1].text=topic
        p.runs[2].text=''
        p.runs[3].text=''
        # Drop the empty trailing spacer so a longer topic cannot create a blank page.
        last=self.doc.paragraphs[-1]
        if not last.text.strip():last._element.getparent().remove(last._element)
        self.md=[f'# Практическая работа {number}\n\n{topic}\n']
        for name,size,bold in [('ReportBody',12,False),('ReportHeading',14,True),('ReportCaption',10,False),('ReportCell',10.5,False),('ReportCode',9,False)]:
            s=self.doc.styles.add_style(name,WD_STYLE_TYPE.PARAGRAPH)
            s.font.name='Consolas' if name=='ReportCode' else 'Times New Roman';s.font.size=Pt(size);s.font.bold=bold;s.font.color.rgb=RGBColor(0,0,0)
            s.paragraph_format.space_after=Pt(6);s.paragraph_format.line_spacing=1.1
            if name=='ReportHeading':s.paragraph_format.keep_with_next=True;s.paragraph_format.space_before=Pt(8)
        sec=self.doc.add_section(WD_SECTION_START.NEW_PAGE)
        sec.top_margin=sec.bottom_margin=sec.left_margin=sec.right_margin=Cm(2)
    def p(self,text,style='ReportBody'):
        p=self.doc.add_paragraph(text,style);self.md.append(text+'\n');return p
    def h(self,text):self.p(text,'ReportHeading');self.md[-1]='## '+text+'\n'
    def page(self):self.doc.add_page_break()
    def table(self,headers,rows,widths=None):
        t=self.doc.add_table(rows=1, cols=len(headers));t.autofit=False
        borders=OxmlElement('w:tblBorders')
        for edge in ['top','left','bottom','right','insideH','insideV']:
            b=OxmlElement('w:'+edge);b.set(qn('w:val'),'single');b.set(qn('w:sz'),'4');b.set(qn('w:color'),'808080');borders.append(b)
        t._tbl.tblPr.append(borders)
        if widths:
            for c,w in zip(t.columns,widths):c.width=Cm(w)
        for c,txt in zip(t.rows[0].cells,headers):c.text=txt
        repeat=OxmlElement('w:tblHeader');t.rows[0]._tr.get_or_add_trPr().append(repeat)
        for row in rows:
            cells=t.add_row().cells
            for c,txt in zip(cells,row):c.text=str(txt)
        for i,row in enumerate(t.rows):
            cant=OxmlElement('w:cantSplit');row._tr.get_or_add_trPr().append(cant)
            for c in row.cells:
                for p in c.paragraphs:
                    p.style='ReportCell';p.paragraph_format.space_after=Pt(3);p.paragraph_format.space_before=Pt(3)
                    if i==0:
                        for run in p.runs:run.bold=True
        self.md.append('| '+' | '.join(headers)+' |\n|'+'|'.join('---' for _ in headers)+'|\n'+'\n'.join('| '+' | '.join(str(x).replace('\n','<br>') for x in row)+' |' for row in rows)+'\n')
    def picture(self,name,caption,width=15):
        p=self.doc.add_paragraph(style='ReportBody');p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.add_run().add_picture(str(E/name),width=Cm(width))
        self.p(caption,'ReportCaption');self.md.append(f'![{caption}](../evidence/{name})\n')
    def save(self):
        self.doc.save(OUT/(self.stem+'.docx'));(OUT/(self.stem+'.md')).write_text('\n'.join(self.md),encoding='utf-8')

r=Report('3_1','3.1 Чек-листы и тест-кейсы')
r.h('Цель и результат работы')
r.p('Разработать чек-лист, пять тест-кейсов и баг-репорт для веб-сервиса. Проверен учебный магазин Swag Labs: четыре тест-кейса пройдены, в одном подтверждён дефект сортировки. Сформирован тест-сьют TS-01.')
r.p(ENV)
r.p('Использованы публичные учебные учётные записи standard_user, problem_user и locked_out_user; пароль secret_sauce опубликован на странице сервиса. Реальные аккаунты и покупки не используются.')
r.h('Чек-лист CL-01')
checks=[('CL-01','Вход с корректными данными','AUTH-11'),('CL-02','Пустые логин и пароль','AUTH-01'),('CL-03','Пустой пароль','AUTH-02'),('CL-04','Пустой логин','AUTH-03'),('CL-05','Неверный пароль','AUTH-04'),('CL-06','Неизвестный пользователь','AUTH-05'),('CL-07','Заблокированный пользователь','AUTH-06'),('CL-08','Добавление товара в корзину','TC-02'),('CL-09','Удаление товара из корзины','TC-03'),('CL-10','Сортировка цены standard_user','TC-04'),('CL-11','Сортировка цены problem_user','TC-05'),('CL-12','Выход и защита каталога','AUTH-12')]
r.table(['ID','Проверка','Результат'],[(i,n,R[test]['status']) for i,n,test in checks],[2,11,3])
r.p('Итог чек-листа: 11 PASS, 1 FAIL. FAIL связан с BUG-01. Подробный протокол: evidence/results.json.')
r.page();r.h('Тест-кейсы TC-01 TC-02 TC-03')
cases=[
('TC-01','Авторизация корректного пользователя','Свежая сессия, открыта главная страница.','1. Ввести standard_user. 2. Ввести secret_sauce. 3. Нажать Login.','Открывается каталог /inventory.html.'),
('TC-02','Добавление товара в корзину','Выполнен TC-01, корзина пуста.','1. Нажать Add to cart у Sauce Labs Backpack. 2. Проверить счётчик. 3. Открыть корзину.','Счётчик равен 1; в корзине только Sauce Labs Backpack.'),
('TC-03','Удаление товара из корзины','Выполнен TC-02, открыта корзина.','1. Нажать Remove у Sauce Labs Backpack. 2. Проверить список и счётчик.','Список корзины пуст; счётчик отсутствует.'),
('TC-04','Сортировка цены по возрастанию','Вход standard_user, открыт каталог.','1. Выбрать Price (low to high). 2. Прочитать все цены сверху вниз, слева направо.','Цены: 7.99; 9.99; 15.99; 15.99; 29.99; 49.99 USD.'),
('TC-05','Сортировка проблемного пользователя','Свежая сессия, вход problem_user / secret_sauce, открыт каталог.','1. Записать текущий порядок цен. 2. Выбрать Price (low to high). 3. Сравнить порядок с возрастающим.','Цены упорядочены: 7.99; 9.99; 15.99; 15.99; 29.99; 49.99 USD.')]
for i,(id,title,pre,steps,expected) in enumerate(cases):
    if i==3:r.page();r.h('Тест-кейсы TC-04 TC-05 и тест-сьют')
    r.h(id+' '+title)
    r.p('Приоритет: средний. Предусловие: '+pre)
    r.p('Шаги: '+steps)
    r.p('Ожидаемый результат: '+expected)
    actual=R[id]['actual']
    if id=='TC-05':actual='Порядок до и после выбора одинаков: 29.99; 9.99; 15.99; 49.99; 7.99; 15.99 USD. Минимальная цена остаётся пятой.'
    r.p('Фактический результат: '+actual+'. Статус: '+R[id]['status']+'.')
r.h('Тест-сьют TS-01')
r.p('Состав: TC-01 → TC-02 → TC-03 → TC-04 → TC-05. Первые три проверки образуют последовательность входа, добавления и удаления; перед TC-05 создаётся чистая сессия. TC-04 служит контрольным сравнением для TC-05. Итог: 4 PASS, 1 FAIL, 0 ошибок исполнения.')
r.page();r.h('Баг-репорт BUG-01')
r.table(['Поле','Значение'],[
('Название','У problem_user не применяется сортировка цены по возрастанию'),('Компонент','Каталог, выбор сортировки'),('Серьёзность и приоритет','Major / Medium: функция сортировки недоступна; каталог остаётся доступным'),('Статус','Open'),('Предусловие','Вход problem_user / secret_sauce, страница /inventory.html'),('Шаги','1. Открыть каталог. 2. Выбрать Price (low to high). 3. Сравнить цены.'),('Ожидается','7.99; 9.99; 15.99; 15.99; 29.99; 49.99 USD'),('Получено','29.99; 9.99; 15.99; 49.99; 7.99; 15.99 USD; выбор не применяется'),('Связь','TC-05; CL-11. Контрольная проверка TC-04 проходит.')],[3.4,12.6])
r.picture('bug-sort.png','Рисунок 1 Каталог problem_user после попытки изменить сортировку',13)
r.p('Вывод: подготовлена тестовая документация, дефект воспроизведён и подтверждён снимком экрана. Он относится к намеренно проблемному учебному аккаунту, а не ко всем пользователям сервиса. После исправления необходим повтор TC-05 и регрессия TC-01–TC-04.')
r.save()

r=Report('3_2','3.2 HTTP-запрос и ответ')
r.h('Цель и результат работы')
r.p('Проанализировать HTTP-запрос и ответ для сайта: определить метод, статус, заголовки и тело. Исследован запрос главного HTML-документа Swag Labs. Получен ответ 200 по HTTP/2, тело запроса отсутствует, тело ответа содержит HTML-каркас приложения.')
r.p(ENV)
r.h('Инструмент и порядок получения данных')
r.p('Сетевые события получены через Chrome DevTools Protocol, домен Network: Network.enable, Network.requestWillBeSent, Network.requestWillBeSentExtraInfo, Network.responseReceived и Network.getResponseBody. Это программный интерфейс DevTools. Для анализа сохранён исходный протокол CDP.')
r.p('Запуск выполнен в новой сессии браузера без пользовательских cookies. Анализируется основной Document, а не запрос JS, изображения или API. Отслеживание завершено после DOMContentLoaded; тело получено отдельно.')
r.h('Структура URL и результат')
r.table(['Элемент','Значение'],[('Схема','https'),('Хост','www.saucedemo.com'),('Порт','443 по умолчанию'),('Путь','/'),('Query и fragment','Отсутствуют'),('Метод',HTTP['request']['method']),('Статус',str(HTTP['response']['status'])+' успешная выдача документа'),('Протокол',HTTP['response']['protocol']+' означает HTTP/2'),('Тип',HTTP['response']['mimeType'])],[4,12])
r.p('Путь взаимодействия: браузер формирует GET-запрос → сервер/CDN возвращает HTML → браузер загружает скрипты и строит интерфейс. Переход на страницу входа сам по себе не является отправкой данных авторизации.')
r.page();r.h('Заголовки запроса')
req=HTTP['request']['headers']
descs={':authority':'Адрес целевого узла',':method':'Метод запроса',':path':'Путь ресурса',':scheme':'Схема соединения','accept':'Допустимые типы ответа','accept-encoding':'Поддерживаемое сжатие','accept-language':'Предпочтительный язык','user-agent':'Браузер и платформа','sec-ch-ua':'Сведения о браузере','sec-ch-ua-mobile':'Признак мобильного браузера','sec-ch-ua-platform':'Платформа','upgrade-insecure-requests':'Предпочтение безопасных ресурсов','sec-fetch-dest':'Назначение ресурса','sec-fetch-mode':'Режим запроса','sec-fetch-site':'Контекст инициатора','sec-fetch-user':'Пользовательская навигация','priority':'Приоритет запроса'}
chosen=[(k,v,descs.get(k.lower(),'Служебный заголовок')) for k,v in req.items() if k.lower() in [':authority',':method',':path',':scheme','accept','accept-encoding','accept-language','user-agent','sec-fetch-dest','sec-fetch-mode']]
if not chosen:chosen=[(k,v,descs.get(k.lower(),'Служебный заголовок')) for k,v in req.items()]
r.table(['Заголовок','Фактическое значение','Назначение'],chosen,[3.5,8.5,4])
r.p('Псевдозаголовки с двоеточием относятся к HTTP/2. Полный набор зафиксированных заголовков находится в evidence/http.json; в таблице приведены основные.')
r.h('Тело запроса')
r.p('В событии запроса отсутствует postData. Для этой навигации GET тело не передавалось; параметры URL также отсутствуют. Нельзя делать вывод об отсутствии тела у всех возможных GET-запросов только на основе одного наблюдения.')
r.page();r.h('Заголовки и тело ответа')
rh=HTTP['response']['headers']
explain={'content-type':'HTML в UTF-8','content-encoding':'Сжатие перед передачей','content-length':'Размер переданного сжатого представления в байтах','cache-control':'Политика кэширования','etag':'Идентификатор представления для проверки актуальности','server':'Заявленное серверное ПО','x-cache':'Состояние кэша CDN','access-control-allow-origin':'Заявленная политика CORS'}
r.table(['Заголовок','Значение','Смысл'],[(k,rh[k],v) for k,v in explain.items() if k in rh],[4,6,6])
html=(E/'response.html').read_text('utf-8')
r.p(f'Декодированное тело сохранено в evidence/response.html: {len(html.encode("utf-8"))} байт. Content-Length относится к сжатому представлению, поэтому может отличаться от размера декодированного HTML.')
r.p('Фрагменты фактического тела ответа:')
import re
fragments=re.findall(r'<title>.*?</title>|<div id="root"[^>]*>.*?</div>|<script[^>]*src=[^>]*></script>',html)
for part in fragments[:4]:r.p(part,'ReportCode')
r.p('HTML содержит корневой контейнер и ссылки на JS-ресурсы. Список товаров и сообщения валидации появляются после выполнения JavaScript; отсутствие их полного текста в исходном HTML не является дефектом.')
r.h('Повторение через графическую панель DevTools')
r.p('1. Открыть сайт и DevTools клавишей F12. 2. Перейти в Network. 3. Очистить список и перезагрузить страницу. 4. Выбрать Document с URL https://www.saucedemo.com/. 5. В Headers проверить Request Method, Status Code, Request Headers и Response Headers. 6. На вкладке Response изучить HTML. Для этого GET раздел Payload не содержит данных формы.')
r.p('Вывод: запрос успешно получает HTML-документ по HTTPS с HTTP/2. Заголовки описывают тип, сжатие и кэширование; статус 200 характеризует получение ресурса и сам по себе не подтверждает исправность всех функций сайта.')
r.save()

r=Report('3_3','3.3 Тестирование авторизации')
r.h('Цель и результат работы')
r.p('Проверить форму авторизации: обязательность полей, корректные и некорректные данные, блокировку пользователя и выход. Выполнено 12 сценариев: 12 PASS, 0 FAIL, 0 ошибок исполнения. Результаты относятся к проверенной форме и выбранным данным.')
r.p(ENV)
r.h('Объект и модель проверок')
r.p('На сервисе доступна авторизация; регистрация в объём этой работы не входит. Поля Username и Password, кнопка Login, текст ошибки. Каждый сценарий входа начинается с очистки cookies и localStorage. Проверки UI выполняются с ожиданием видимости элементов.')
r.table(['Поле','Наблюдение'],[(f['name'],f"type={f['type']}; required={str(f['required']).lower()}; maxLength={f['maxLength']}") for f in RESULT['fields']],[4,12])
r.p('HTML-атрибут required отсутствует; обязательность проверяет приложение после Login. Отсутствие required не означает отсутствия валидации. Пароль имеет тип password. maxLength=-1 означает отсутствие явно заданного HTML-ограничения, а не доказанную неограниченность на всех уровнях.')
r.h('Классы эквивалентности')
r.p('Логин: пустой, существующий, неизвестный, заблокированный, изменённый регистр, пробелы вокруг, строка со спецсимволами. Пароль: пустой, корректный, неверный, изменённый регистр. Граничный случай обязательности: длина 0. Числовые ограничения длины в условиях задания не заданы.')
r.p('Ожидаемые результаты заданы до проверок: валидный пользователь попадает в каталог; невалидные данные не дают доступ; пустые поля вызывают соответствующее сообщение. Для входа с пробелами проверяется буквальное совпадение логина, без требования автоматического удаления пробелов.')
labels=['Оба поля пустые','Пароль пустой','Логин пустой','Неверный пароль','Неизвестный логин','Заблокированный аккаунт','Верхний регистр логина','Верхний регистр пароля','Пробелы вокруг логина','Строка со спецсимволами','Успешный вход','Выход и прямой URL']
expected_short=['Сообщение Username is required','Сообщение Password is required','Сообщение Username is required','Ошибка несовпадения данных','Ошибка несовпадения данных','Сообщение о блокировке','Вход отклонён','Вход отклонён','Вход отклонён','Вход отклонён, каталог недоступен','Каталог и 6 товаров','Каталог закрыт после выхода']
for start,end in [(0,6),(6,12)]:
    r.page();r.h(f'Протокол сценариев AUTH-{start+1:02} AUTH-{end:02}')
    for j in range(start,end):
        id=f'AUTH-{j+1:02}';item=R[id]
        r.h(id+' '+labels[j])
        if j<10:
            u=item['username'] or '(пусто)';p=item['password'] or '(пусто)'
            r.p(f'Данные: Username = «{u}»; Password = «{p}». Шаг: заполнить поля и нажать Login.')
        elif j==10:r.p('Данные: standard_user / secret_sauce. Шаг: войти и дождаться списка товаров.')
        else:r.p('Предусловие: вход standard_user. Шаги: меню → Logout → прямой переход на /inventory.html.')
        r.p('Ожидается: '+expected_short[j]+'. Фактически: '+item['actual']+'. Статус: '+item['status']+'.')
r.page();r.h('Подтверждение результатов')
r.picture('AUTH-01.png','Рисунок 1 Проверка пустых полей и сообщение о необходимости логина',12.5)
r.picture('auth-success.png','Рисунок 2 Успешная авторизация и каталог из шести товаров',12.5)
r.h('Вывод')
r.p('В проверенных сценариях обязательность полей, отказ при неверных данных, блокировка, успешный вход и выход работают ожидаемо. AUTH-10 подтверждает отказ для одной строки со спецсимволами; он не является полным аудитом SQL-инъекций или безопасности. Исходные результаты и снимки сохранены в evidence/.')
r.save()
print('Created three DOCX reports and three Markdown reports')
