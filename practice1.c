#include <stdio.h>  
 
int main(void)
{
    int a, b;       //정수형 변수 2개를 한 줄에 선언
    int sum;        //정수형 변수 1개 선언
 
    a = 10;         //a에 10을 대입
    b = 20;         //b에 20을 대입
 
    sum = a + b;    // a + b 연산 결과를 sum 변수에 대입
    printf("sum = %d\n", sum); //결과를 화면에 출력
 
    return 0;
}
