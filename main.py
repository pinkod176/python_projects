import datetime
import random
import time

# переменные
words = ('космический','электроэнергия','опубликовать','новорожденный','гравировка','благотворительность','грейпфрут','регистрация','жизнерадостный','оптимистичный','удручающий')
alien_races = {'мфрсианин':(1, 1), 'Ануннаки':(1, 1), 'Рептилоиды':(1, 1), 'Плеядеанцы':(1, 1), 'Кассиопеяне':(1, 1)}
run = True
# классы
class Alien:
    def __init__(self):
        self.name = random.choice(list(alien_races.keys()))
        self.life = alien_races[self.name][0]
        self.damage = alien_races[self.name][1]
    def attack(self):
        words_1 = random.choice(words)
        return words_1
class Ninja:
    def __init__(self):
        self.score = 0
    def defend(self, word):
        global run
        time1 = datetime.datetime.now().timestamp()
        
        print('Отбивайся!')
        word_2 = input()
        time2 = datetime.datetime.now().timestamp()
        time3 = (time2 - time1)
        if word_2 == word and time3 <= 5:
            self.score += 1
            print(f'Твой счет: {self.score}')
        else:
            print(f'Ты проиграл, твой счет {self.score}')
            run = False
        
# основной код
ninja = Ninja()
print('Добро пожаловать в игру "Космический ниндзя"')
print('Ты — Космический Ниндзя\nТвоя задача охранять вход в город от инопланетян, они так и норовятворваться и всё разгромить.\nТы обученный боец, который провёл всю жизнь в тренировках и выучил все атаки инопланетян')
for i in '.....':
    print(i)
    time.sleep(1)
# главный цикл
while run:
    alien = Alien()
    print(f'Вас атакует {alien.name}')
    
    alien_attack = alien.attack()
    print(f'название атаки - {alien_attack}')
    for x in '...':
        print(x)
        time.sleep(0.6)
    ninja.defend(word = alien_attack)