from interpreter import Interpreter

def main():
    print("Welcome to the Chatbot/Note-Taking Interface!")
    print("Type /help for available commands")
    interpreter = Interpreter()

    while True:
        try:
            user_input = input("\nYou: ")
            if user_input.lower() in ["/exit", "/quit"]:
                print("Goodbye!")
                break
                
            response = interpreter.handle_input(user_input)
            print(f"Bot: {response}")/
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
