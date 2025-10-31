run_block = false;
document.addEventListener('DOMContentLoaded', function() {

    const terminal = document.getElementById('terminal');
    const socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port);
   

    //listener

    terminal.addEventListener('click', function() {
        // Asegurarte de que este es tu selector correcto para el input.
        const input = document.querySelector('#terminal .input-line input');
        if(input) {
            input.focus({ preventScroll: true });
        }
    });

    document.querySelectorAll('.play-btn').forEach(function(button) {
      button.addEventListener('click', function() {
        if(!run_block){
          const mediaName = this.getAttribute('data-media-name');
          const command = `python cli.py --media ${mediaName} --params direct`;
          
          // Remover el input si existe antes de ejecutar
          const existingInput = document.querySelector('#terminal .input-line');
          if(existingInput) {
            existingInput.remove();
          }
          
          // Hacer scroll hacia el CLI
          const cliSection = document.getElementById('terminal');
          if(cliSection) {
            cliSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }
          
          // Emitir el comando directamente
          addLine(command, true);
          socket.emit('execute_command', command);
        }else{
          alert('Wait for the current run to finish.');
        }
      });
    });

    // Función para hacer scroll al final del terminal
    function scrollToBottom() {
        terminal.scrollTop = terminal.scrollHeight;
    }

    // Función modificada para agregar líneas de texto al terminal
    function addLine(text, isCommand=false) {
        const codeElement = terminal.querySelector('code');
        if(isCommand) {
            codeElement.textContent += '$ ' + text + '\n';
        } else {
            codeElement.textContent += text + '\n';
        }
        
        // Realiza el scroll automático después de cada agregación
        scrollToBottom();
    }
    
    // Función para gestionar la entrada de comandos
    function handleCommandInput() {
        const codeElement = terminal.querySelector('code');
        const inputLine = document.createElement('div');
        inputLine.className = 'input-line flex items-center gap-2';
        inputLine.style.cssText = 'margin-top: 8px;';
        const prompt = document.createElement('span');
        prompt.textContent = '$ ';
        prompt.style.cssText = 'color: #9ca3af;';
        const input = document.createElement('input');
        input.type = 'text';
        input.style.cssText = 'background: transparent; border: none; outline: none; color: #d1d5db; flex: 1; font-family: monospace; font-size: 0.875rem;';
        inputLine.appendChild(prompt);
        inputLine.appendChild(input);
        terminal.appendChild(inputLine);
        
        // Hacer focus sin scroll automático
        input.focus({ preventScroll: true });
        
        input.addEventListener('keydown', function(event) {
            if(event.key === 'Enter' && input.value.trim() !== '') {
                const command = input.value.trim();
                addLine(command, true); // Refleja el comando en el terminal
                socket.emit('execute_command', command);
                inputLine.remove(); // Asegúrate de remover el inputLine
            }
        });
    }

    // Escuchadores de eventos (listeners) de Socket.IO
    
    socket.on('connect', function() {
        // El servidor enviará el estado de ejecución, esperamos a recibirlo
    });

    socket.on('execution_status', function(data) {
        // Ocultar skeleton y mostrar contenido real
        const skeleton = document.getElementById('cli-skeleton');
        const cliContent = terminal.querySelector('pre');
        if(skeleton) {
            skeleton.classList.add('hidden');
        }
        if(cliContent) {
            cliContent.classList.remove('hidden');
        }
        
        // Sincronizar el estado de ejecución con el servidor
        run_block = data.is_running;
        
        // Solo crear el input si no hay ejecución en curso
        if(!run_block) {
            // Remover input existente si lo hay
            const existingInput = document.querySelector('#terminal .input-line');
            if(existingInput) {
                existingInput.remove();
            }
            handleCommandInput();
        }
        
        // Hacer scroll al final después de cargar el historial
        setTimeout(scrollToBottom, 100);
    });

    socket.on('execution_started', function() {
        // Marcar que hay una ejecución en curso
        run_block = true;
        // Remover el input si existe
        const existingInput = document.querySelector('#terminal .input-line');
        if(existingInput) {
            existingInput.remove();
        }
    });

    socket.on('command_output', function(msg) {
        addLine(msg, false); // Asegúrate de que 'msg' sea el mensaje en sí, sin envoltura {}
    });
    
    // Escucha para cuando un comando ha finalizado
    socket.on('command_completed', function() {
        run_block = false;
        // Remover input existente si lo hay antes de crear uno nuevo
        const existingInput = document.querySelector('#terminal .input-line');
        if(existingInput) {
            existingInput.remove();
        }
        handleCommandInput(); // Asegura que el input se vuelva a crear y esté listo para el siguiente comando
        
        // Hacer scroll al final
        setTimeout(scrollToBottom, 50);
    });
});
