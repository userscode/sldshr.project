import streamlit as st
import streamlit.components.v1 as components

# Устанавливаем широкий режим для лучшего отображения игры
st.set_page_config(page_title="3D Игра на Streamlit", layout="wide")

st.title("🎮 3D Endless Runner в Streamlit")
st.markdown("""
**Как играть:**
1. **Кликните мышкой** по черному экрану игры, чтобы он перехватил управление с клавиатуры.
2. Используйте **стрелки Влево/Вправо** или клавиши **A/D** для перемещения.
3. Уворачивайтесь от красных препятствий!
""")

# Этот код будет запущен внутри изолированного iframe в Streamlit
html_code = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>3D Game</title>
    <style>
        /* Убираем отступы и скрываем полосы прокрутки для полноэкранного канваса */
        body { margin: 0; overflow: hidden; background-color: #111; font-family: 'Segoe UI', sans-serif; }
        
        /* Стили для счета */
        #score-board { 
            position: absolute; 
            top: 15px; 
            left: 20px; 
            color: #00ffcc; 
            font-size: 28px; 
            font-weight: bold; 
            z-index: 100; 
            text-shadow: 0 0 10px rgba(0, 255, 204, 0.5); 
        }
        
        /* Стили для экрана проигрыша */
        #game-over { 
            position: absolute; 
            top: 50%; 
            left: 50%; 
            transform: translate(-50%, -50%); 
            color: white; 
            font-size: 48px; 
            font-weight: bold; 
            z-index: 100; 
            display: none; 
            text-align: center; 
            background: rgba(20, 20, 20, 0.9); 
            padding: 40px; 
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.8);
            border: 2px solid #ff3333;
        }
        
        /* Кнопка рестарта */
        #restart-btn { 
            margin-top: 30px; 
            font-size: 22px; 
            padding: 15px 30px; 
            cursor: pointer; 
            background: linear-gradient(45deg, #ff3333, #ff0066); 
            border: none; 
            color: white; 
            border-radius: 10px; 
            font-weight: bold;
            transition: transform 0.2s;
        }
        #restart-btn:hover {
            transform: scale(1.05);
        }
        
        /* Подсказка для пользователя */
        #focus-hint {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: rgba(255,255,255,0.7);
            font-size: 24px;
            pointer-events: none;
            z-index: 50;
            transition: opacity 0.5s;
        }
    </style>
</head>
<body>
    <div id="score-board">СЧЕТ: <span id="score">0</span></div>
    <div id="focus-hint">Кликните здесь, чтобы начать!</div>
    
    <div id="game-over">
        <div style="color: #ff3333; text-shadow: 0 0 20px #ff3333;">ИГРА ОКОНЧЕНА</div>
        <div style="font-size: 24px; margin-top: 15px; color: #ccc;">Ваш итоговый счет: <span id="final-score">0</span></div>
        <button id="restart-btn">ИГРАТЬ СНОВА</button>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script>
        // Инициализация сцены Three.js
        const scene = new THREE.Scene();
        // Добавляем туман для эффекта "появления" объектов вдалеке
        scene.fog = new THREE.Fog(0x111111, 10, 60);

        // Настройка камеры
        const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
        camera.position.set(0, 4, 8);
        camera.lookAt(0, 0, -10);

        // Настройка рендерера
        const renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setSize(window.innerWidth, window.innerHeight);
        document.body.appendChild(renderer.domElement);

        // Настройка освещения
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
        scene.add(ambientLight);
        
        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(10, 20, 10);
        scene.add(directionalLight);

        // Создание Игрока (Кибер-куб)
        const playerGeometry = new THREE.BoxGeometry(1, 1, 1);
        const playerMaterial = new THREE.MeshStandardMaterial({ 
            color: 0x00ffcc, 
            emissive: 0x004433,
            roughness: 0.2,
            metalness: 0.8
        });
        const player = new THREE.Mesh(playerGeometry, playerMaterial);
        player.position.y = 0.5;
        scene.add(player);

        // Создание бесконечной сетки-пола в стиле Tron
        const gridHelper = new THREE.GridHelper(200, 100, 0x00ffcc, 0x222222);
        gridHelper.position.y = 0;
        scene.add(gridHelper);

        // Игровые переменные
        let obstacles = [];
        let baseSpeed = 0.25;
        let speed = baseSpeed;
        let score = 0;
        let gameOver = false;
        let gameStarted = false;
        
        // Отслеживание нажатий клавиш
        let keys = { ArrowLeft: false, ArrowRight: false, a: false, d: false };

        // Убираем подсказку при первом клике и активируем игру
        document.body.addEventListener('click', () => {
            if(!gameStarted) {
                document.getElementById('focus-hint').style.opacity = '0';
                gameStarted = true;
                spawnObstacle();
            }
        });

        window.addEventListener('keydown', (e) => {
            if (keys.hasOwnProperty(e.key) || e.key.toLowerCase() === 'a' || e.key.toLowerCase() === 'd') {
                keys[e.key] = true;
                if(e.key === 'a' || e.key === 'A') keys['a'] = true;
                if(e.key === 'd' || e.key === 'D') keys['d'] = true;
            }
        });

        window.addEventListener('keyup', (e) => {
            if (keys.hasOwnProperty(e.key) || e.key.toLowerCase() === 'a' || e.key.toLowerCase() === 'd') {
                keys[e.key] = false;
                if(e.key === 'a' || e.key === 'A') keys['a'] = false;
                if(e.key === 'd' || e.key === 'D') keys['d'] = false;
            }
        });

        // Функция генерации препятствий
        function spawnObstacle() {
            if (gameOver || !gameStarted) return;
            
            const geometry = new THREE.BoxGeometry(1.5, 1.5, 1.5);
            const material = new THREE.MeshStandardMaterial({ 
                color: 0xff3333,
                emissive: 0x440000,
                roughness: 0.1
            });
            const obstacle = new THREE.Mesh(geometry, material);
            
            // Выбираем случайную полосу для появления (от -6 до 6)
            const xPos = Math.floor(Math.random() * 13) - 6; 
            obstacle.position.set(xPos, 0.75, -80); // Появляются далеко впереди
            
            scene.add(obstacle);
            obstacles.push(obstacle);

            // Чем выше счет, тем быстрее появляются новые препятствия
            let spawnRate = Math.max(300, 1200 - (score * 15));
            setTimeout(spawnObstacle, spawnRate);
        }

        document.getElementById('restart-btn').addEventListener('click', (e) => {
            e.stopPropagation(); // Чтобы клик не засчитывался фоном
            
            // Очистка старых препятствий
            obstacles.forEach(obs => scene.remove(obs));
            obstacles = [];
            
            // Сброс параметров
            score = 0;
            speed = baseSpeed;
            gameOver = false;
            player.position.x = 0;
            
            // Обновление UI
            document.getElementById('score').innerText = score;
            document.getElementById('game-over').style.display = 'none';
            
            // Перезапуск
            spawnObstacle();
        });

        function animate() {
            requestAnimationFrame(animate);

            if (gameOver || !gameStarted) {
                renderer.render(scene, camera);
                return;
            }

            // Плавное движение игрока
            const moveSpeed = 0.35;
            if ((keys.ArrowLeft || keys.a) && player.position.x > -6.5) player.position.x -= moveSpeed;
            if ((keys.ArrowRight || keys.d) && player.position.x < 6.5) player.position.x += moveSpeed;

            // Анимация сетки (иллюзия движения вперед)
            gridHelper.position.z = (gridHelper.position.z + speed) % 10;

            // Движение препятствий и проверка столкновений
            for (let i = obstacles.length - 1; i >= 0; i--) {
                let obs = obstacles[i];
                obs.position.z += speed; // Препятствие двигается на нас
                
                // Вращение для красоты
                obs.rotation.x += 0.02;
                obs.rotation.y += 0.02;

                // Простая AABB коллизия (проверка расстояния по осям X и Z)
                const hitDistX = 1.2; // Ширина хитбокса
                const hitDistZ = 1.2; // Глубина хитбокса
                
                if (Math.abs(player.position.x - obs.position.x) < hitDistX &&
                    Math.abs(player.position.z - obs.position.z) < hitDistZ) {
                    
                    gameOver = true;
                    document.getElementById('final-score').innerText = score;
                    document.getElementById('game-over').style.display = 'block';
                    break; 
                }

                // Удаление пройденных препятствий с начислением очков
                if (obs.position.z > 10) {
                    scene.remove(obs);
                    obstacles.splice(i, 1);
                    score += 10;
                    document.getElementById('score').innerText = score;
                    speed += 0.002; // Постепенно увеличиваем скорость игры
                }
            }

            // Небольшая покачивающаяся анимация камеры для эффекта скорости
            camera.position.x = player.position.x * 0.1;
            camera.lookAt(0, 0, -10);

            renderer.render(scene, camera);
        }

        // Адаптация под размер фрейма Streamlit
        window.addEventListener('resize', () => {
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        });

        // Запуск цикла рендера
        animate();
    </script>
</body>
</html>
"""

# Встраиваем нашу игру высотой 650 пикселей.
# scrolling=False гарантирует, что внутри игры не появится полоса прокрутки браузера.
components.html(html_code, height=650, scrolling=False)

st.caption("Разработано с помощью Python (Streamlit) и JavaScript (Three.js)")
