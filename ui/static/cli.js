run_block = false;
document.addEventListener('DOMContentLoaded', function() {

    const terminal = document.getElementById('terminal');
    const socket = io.connect('http://' + document.domain + ':' + location.port);
   

    //listener

    terminal.addEventListener('click', function() {
        // Asegurarte de que este es tu selector correcto para el input.
        const input = document.querySelector('#terminal .input-line input');
        if(input) {
            input.focus();
        }
    });

    document.querySelectorAll('.play-btn').forEach(function(button) {
      button.addEventListener('click', function() {
        if(!run_block){
          run_block = true;
          const mediaName = this.getAttribute('data-media-name');
          const command = `python cli.py --media ${mediaName} --params direct`;
          
          // Asume que esta función simula escribir el comando y presionar 'Enter'.
          // Si no tienes una función como esta, tendrías que implementar una.
          emitCommand(command);
        }else{
          alert('Wait for the current run to finish.');
        }
      });
    });

    // Función modificada para agregar líneas de texto al terminal
    function addLine(text, isCommand=false) {
        const line = document.createElement('div');
        if(isCommand) {
            const prompt = document.createElement('span');
            prompt.textContent = '$ ';
            line.appendChild(prompt);
            const content = document.createElement('span');
            content.textContent = text;
            line.appendChild(content);
        } else {
            line.textContent = text;
        }
        terminal.appendChild(line);
        
        // Realiza el scroll automático después de cada agregación
        terminal.scrollTop = terminal.scrollHeight;
    }
    
    // Función para gestionar la entrada de comandos
    function handleCommandInput() {
        const inputLine = document.createElement('div');
        inputLine.className = 'input-line';
        const prompt = document.createElement('span');
        prompt.textContent = '$ ';
        const input = document.createElement('input');
        input.type = 'text';
        inputLine.appendChild(prompt);
        inputLine.appendChild(input);
        terminal.appendChild(inputLine);
        input.focus();
        
        input.addEventListener('keydown', function(event) {
            if(event.key === 'Enter' && input.value.trim() !== '') {
                const command = input.value.trim();
                socket.emit('execute_command', command);
                
                addLine(command, true); // Refleja el comando en el terminal
                inputLine.remove(); // Asegúrate de remover el inputLine
            }
        });
    }
    function emitCommand(command) {
      const input = document.querySelector('#terminal .input-line input');

      if(input) {
        // Establece el valor del comando en el input.
        input.value = command;
        
        // Crea un nuevo evento 'keydown' y configura 'key' como 'Enter'.
        let event = new KeyboardEvent('keydown', { key: 'Enter' });
        
        // Dispara el evento 'keydown' en el input.
        // Nota: Algunos navegadores pueden no permitir simular eventos de teclado de esta manera para acciones protegidas.
        input.dispatchEvent(event);
      }
    }

    // Escuchadores de eventos (listeners) de Socket.IO
    
    socket.on('connect', function() {
        // addLine("Connected to server.", false);
        // No necesitamos llamar a handleCommandInput() aquí puesto que se llama después de 'command_completed'
    });

    socket.on('command_output', function(msg) {
        addLine(msg, false); // Asegúrate de que 'msg' sea el mensaje en sí, sin envoltura {}
    });
    
    // Escucha para cuando un comando ha finalizado
    socket.on('command_completed', function() {
        run_block = false;
        handleCommandInput(); // Asegura que el input se vuelva a crear y esté listo para el siguiente comando
    });

    // Inicializa el primer prompt
    handleCommandInput(); 
});
