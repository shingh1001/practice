#include <stdio.h>
 
int main()
{
    int a, b;
    char ch;
 
    printf("수식을 한줄로 띄어쓰기로 입력하세요 : ");
    scanf("%d %c %d", &a, &ch, &b); // 일반 수식처럼 띄어쓰기를 해서 한줄에 변수 3개를 입력
 
    switch (ch)
    {
    case '+':
        printf("%d + %d = %d 입니다. \n", a, b, a + b);
        break;
    case '-':
        printf("%d - %d = %d 입니다. \n", a, b, a - b);
        break;
    case '*':
        printf("%d * %d = %d 입니다. \n", a, b, a*b);
        break;
    case '/':
        printf("%d / %d = %d 입니다. \n", a, b, a / b);
        break;
    case '%':
        printf("%d %% %d = %d 입니다. \n", a, b, a%b);
        break;
    default:
        printf("연산자를 잘못 입력했습니다. \n");
    }
}
