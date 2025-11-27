# Generated from mflang/grammar/MFLang.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .MFLangParser import MFLangParser
else:
    from MFLangParser import MFLangParser

# This class defines a complete listener for a parse tree produced by MFLangParser.
class MFLangListener(ParseTreeListener):

    # Enter a parse tree produced by MFLangParser#program.
    def enterProgram(self, ctx:MFLangParser.ProgramContext):
        pass

    # Exit a parse tree produced by MFLangParser#program.
    def exitProgram(self, ctx:MFLangParser.ProgramContext):
        pass


    # Enter a parse tree produced by MFLangParser#statement.
    def enterStatement(self, ctx:MFLangParser.StatementContext):
        pass

    # Exit a parse tree produced by MFLangParser#statement.
    def exitStatement(self, ctx:MFLangParser.StatementContext):
        pass


    # Enter a parse tree produced by MFLangParser#importStatement.
    def enterImportStatement(self, ctx:MFLangParser.ImportStatementContext):
        pass

    # Exit a parse tree produced by MFLangParser#importStatement.
    def exitImportStatement(self, ctx:MFLangParser.ImportStatementContext):
        pass


    # Enter a parse tree produced by MFLangParser#periodType.
    def enterPeriodType(self, ctx:MFLangParser.PeriodTypeContext):
        pass

    # Exit a parse tree produced by MFLangParser#periodType.
    def exitPeriodType(self, ctx:MFLangParser.PeriodTypeContext):
        pass


    # Enter a parse tree produced by MFLangParser#variableDeclaration.
    def enterVariableDeclaration(self, ctx:MFLangParser.VariableDeclarationContext):
        pass

    # Exit a parse tree produced by MFLangParser#variableDeclaration.
    def exitVariableDeclaration(self, ctx:MFLangParser.VariableDeclarationContext):
        pass


    # Enter a parse tree produced by MFLangParser#variableAssignment.
    def enterVariableAssignment(self, ctx:MFLangParser.VariableAssignmentContext):
        pass

    # Exit a parse tree produced by MFLangParser#variableAssignment.
    def exitVariableAssignment(self, ctx:MFLangParser.VariableAssignmentContext):
        pass


    # Enter a parse tree produced by MFLangParser#tradingInstruction.
    def enterTradingInstruction(self, ctx:MFLangParser.TradingInstructionContext):
        pass

    # Exit a parse tree produced by MFLangParser#tradingInstruction.
    def exitTradingInstruction(self, ctx:MFLangParser.TradingInstructionContext):
        pass


    # Enter a parse tree produced by MFLangParser#tradingCmd.
    def enterTradingCmd(self, ctx:MFLangParser.TradingCmdContext):
        pass

    # Exit a parse tree produced by MFLangParser#tradingCmd.
    def exitTradingCmd(self, ctx:MFLangParser.TradingCmdContext):
        pass


    # Enter a parse tree produced by MFLangParser#tCommandStatement.
    def enterTCommandStatement(self, ctx:MFLangParser.TCommandStatementContext):
        pass

    # Exit a parse tree produced by MFLangParser#tCommandStatement.
    def exitTCommandStatement(self, ctx:MFLangParser.TCommandStatementContext):
        pass


    # Enter a parse tree produced by MFLangParser#ifThenBlock.
    def enterIfThenBlock(self, ctx:MFLangParser.IfThenBlockContext):
        pass

    # Exit a parse tree produced by MFLangParser#ifThenBlock.
    def exitIfThenBlock(self, ctx:MFLangParser.IfThenBlockContext):
        pass


    # Enter a parse tree produced by MFLangParser#blockStatement.
    def enterBlockStatement(self, ctx:MFLangParser.BlockStatementContext):
        pass

    # Exit a parse tree produced by MFLangParser#blockStatement.
    def exitBlockStatement(self, ctx:MFLangParser.BlockStatementContext):
        pass


    # Enter a parse tree produced by MFLangParser#emptyStatement.
    def enterEmptyStatement(self, ctx:MFLangParser.EmptyStatementContext):
        pass

    # Exit a parse tree produced by MFLangParser#emptyStatement.
    def exitEmptyStatement(self, ctx:MFLangParser.EmptyStatementContext):
        pass


    # Enter a parse tree produced by MFLangParser#ComparisonExpression.
    def enterComparisonExpression(self, ctx:MFLangParser.ComparisonExpressionContext):
        pass

    # Exit a parse tree produced by MFLangParser#ComparisonExpression.
    def exitComparisonExpression(self, ctx:MFLangParser.ComparisonExpressionContext):
        pass


    # Enter a parse tree produced by MFLangParser#AdditiveExpression.
    def enterAdditiveExpression(self, ctx:MFLangParser.AdditiveExpressionContext):
        pass

    # Exit a parse tree produced by MFLangParser#AdditiveExpression.
    def exitAdditiveExpression(self, ctx:MFLangParser.AdditiveExpressionContext):
        pass


    # Enter a parse tree produced by MFLangParser#AndExpression.
    def enterAndExpression(self, ctx:MFLangParser.AndExpressionContext):
        pass

    # Exit a parse tree produced by MFLangParser#AndExpression.
    def exitAndExpression(self, ctx:MFLangParser.AndExpressionContext):
        pass


    # Enter a parse tree produced by MFLangParser#OrKeywordExpression.
    def enterOrKeywordExpression(self, ctx:MFLangParser.OrKeywordExpressionContext):
        pass

    # Exit a parse tree produced by MFLangParser#OrKeywordExpression.
    def exitOrKeywordExpression(self, ctx:MFLangParser.OrKeywordExpressionContext):
        pass


    # Enter a parse tree produced by MFLangParser#NotKeywordExpression.
    def enterNotKeywordExpression(self, ctx:MFLangParser.NotKeywordExpressionContext):
        pass

    # Exit a parse tree produced by MFLangParser#NotKeywordExpression.
    def exitNotKeywordExpression(self, ctx:MFLangParser.NotKeywordExpressionContext):
        pass


    # Enter a parse tree produced by MFLangParser#NotExpression.
    def enterNotExpression(self, ctx:MFLangParser.NotExpressionContext):
        pass

    # Exit a parse tree produced by MFLangParser#NotExpression.
    def exitNotExpression(self, ctx:MFLangParser.NotExpressionContext):
        pass


    # Enter a parse tree produced by MFLangParser#UnaryExpression.
    def enterUnaryExpression(self, ctx:MFLangParser.UnaryExpressionContext):
        pass

    # Exit a parse tree produced by MFLangParser#UnaryExpression.
    def exitUnaryExpression(self, ctx:MFLangParser.UnaryExpressionContext):
        pass


    # Enter a parse tree produced by MFLangParser#PrimaryExpr.
    def enterPrimaryExpr(self, ctx:MFLangParser.PrimaryExprContext):
        pass

    # Exit a parse tree produced by MFLangParser#PrimaryExpr.
    def exitPrimaryExpr(self, ctx:MFLangParser.PrimaryExprContext):
        pass


    # Enter a parse tree produced by MFLangParser#OrExpression.
    def enterOrExpression(self, ctx:MFLangParser.OrExpressionContext):
        pass

    # Exit a parse tree produced by MFLangParser#OrExpression.
    def exitOrExpression(self, ctx:MFLangParser.OrExpressionContext):
        pass


    # Enter a parse tree produced by MFLangParser#AndKeywordExpression.
    def enterAndKeywordExpression(self, ctx:MFLangParser.AndKeywordExpressionContext):
        pass

    # Exit a parse tree produced by MFLangParser#AndKeywordExpression.
    def exitAndKeywordExpression(self, ctx:MFLangParser.AndKeywordExpressionContext):
        pass


    # Enter a parse tree produced by MFLangParser#MultiplicativeExpression.
    def enterMultiplicativeExpression(self, ctx:MFLangParser.MultiplicativeExpressionContext):
        pass

    # Exit a parse tree produced by MFLangParser#MultiplicativeExpression.
    def exitMultiplicativeExpression(self, ctx:MFLangParser.MultiplicativeExpressionContext):
        pass


    # Enter a parse tree produced by MFLangParser#LiteralExpr.
    def enterLiteralExpr(self, ctx:MFLangParser.LiteralExprContext):
        pass

    # Exit a parse tree produced by MFLangParser#LiteralExpr.
    def exitLiteralExpr(self, ctx:MFLangParser.LiteralExprContext):
        pass


    # Enter a parse tree produced by MFLangParser#IdentifierExpr.
    def enterIdentifierExpr(self, ctx:MFLangParser.IdentifierExprContext):
        pass

    # Exit a parse tree produced by MFLangParser#IdentifierExpr.
    def exitIdentifierExpr(self, ctx:MFLangParser.IdentifierExprContext):
        pass


    # Enter a parse tree produced by MFLangParser#KlineDataExpr.
    def enterKlineDataExpr(self, ctx:MFLangParser.KlineDataExprContext):
        pass

    # Exit a parse tree produced by MFLangParser#KlineDataExpr.
    def exitKlineDataExpr(self, ctx:MFLangParser.KlineDataExprContext):
        pass


    # Enter a parse tree produced by MFLangParser#FunctionCallExpr.
    def enterFunctionCallExpr(self, ctx:MFLangParser.FunctionCallExprContext):
        pass

    # Exit a parse tree produced by MFLangParser#FunctionCallExpr.
    def exitFunctionCallExpr(self, ctx:MFLangParser.FunctionCallExprContext):
        pass


    # Enter a parse tree produced by MFLangParser#CrossPeriodRefExpr.
    def enterCrossPeriodRefExpr(self, ctx:MFLangParser.CrossPeriodRefExprContext):
        pass

    # Exit a parse tree produced by MFLangParser#CrossPeriodRefExpr.
    def exitCrossPeriodRefExpr(self, ctx:MFLangParser.CrossPeriodRefExprContext):
        pass


    # Enter a parse tree produced by MFLangParser#ParenExpr.
    def enterParenExpr(self, ctx:MFLangParser.ParenExprContext):
        pass

    # Exit a parse tree produced by MFLangParser#ParenExpr.
    def exitParenExpr(self, ctx:MFLangParser.ParenExprContext):
        pass


    # Enter a parse tree produced by MFLangParser#literal.
    def enterLiteral(self, ctx:MFLangParser.LiteralContext):
        pass

    # Exit a parse tree produced by MFLangParser#literal.
    def exitLiteral(self, ctx:MFLangParser.LiteralContext):
        pass


    # Enter a parse tree produced by MFLangParser#integer.
    def enterInteger(self, ctx:MFLangParser.IntegerContext):
        pass

    # Exit a parse tree produced by MFLangParser#integer.
    def exitInteger(self, ctx:MFLangParser.IntegerContext):
        pass


    # Enter a parse tree produced by MFLangParser#float.
    def enterFloat(self, ctx:MFLangParser.FloatContext):
        pass

    # Exit a parse tree produced by MFLangParser#float.
    def exitFloat(self, ctx:MFLangParser.FloatContext):
        pass


    # Enter a parse tree produced by MFLangParser#booleanLiteral.
    def enterBooleanLiteral(self, ctx:MFLangParser.BooleanLiteralContext):
        pass

    # Exit a parse tree produced by MFLangParser#booleanLiteral.
    def exitBooleanLiteral(self, ctx:MFLangParser.BooleanLiteralContext):
        pass


    # Enter a parse tree produced by MFLangParser#stringLiteral.
    def enterStringLiteral(self, ctx:MFLangParser.StringLiteralContext):
        pass

    # Exit a parse tree produced by MFLangParser#stringLiteral.
    def exitStringLiteral(self, ctx:MFLangParser.StringLiteralContext):
        pass


    # Enter a parse tree produced by MFLangParser#klineData.
    def enterKlineData(self, ctx:MFLangParser.KlineDataContext):
        pass

    # Exit a parse tree produced by MFLangParser#klineData.
    def exitKlineData(self, ctx:MFLangParser.KlineDataContext):
        pass


    # Enter a parse tree produced by MFLangParser#functionCall.
    def enterFunctionCall(self, ctx:MFLangParser.FunctionCallContext):
        pass

    # Exit a parse tree produced by MFLangParser#functionCall.
    def exitFunctionCall(self, ctx:MFLangParser.FunctionCallContext):
        pass


    # Enter a parse tree produced by MFLangParser#refFunction.
    def enterRefFunction(self, ctx:MFLangParser.RefFunctionContext):
        pass

    # Exit a parse tree produced by MFLangParser#refFunction.
    def exitRefFunction(self, ctx:MFLangParser.RefFunctionContext):
        pass


    # Enter a parse tree produced by MFLangParser#barslastFunction.
    def enterBarslastFunction(self, ctx:MFLangParser.BarslastFunctionContext):
        pass

    # Exit a parse tree produced by MFLangParser#barslastFunction.
    def exitBarslastFunction(self, ctx:MFLangParser.BarslastFunctionContext):
        pass


    # Enter a parse tree produced by MFLangParser#sumbarsFunction.
    def enterSumbarsFunction(self, ctx:MFLangParser.SumbarsFunctionContext):
        pass

    # Exit a parse tree produced by MFLangParser#sumbarsFunction.
    def exitSumbarsFunction(self, ctx:MFLangParser.SumbarsFunctionContext):
        pass


    # Enter a parse tree produced by MFLangParser#hhvFunction.
    def enterHhvFunction(self, ctx:MFLangParser.HhvFunctionContext):
        pass

    # Exit a parse tree produced by MFLangParser#hhvFunction.
    def exitHhvFunction(self, ctx:MFLangParser.HhvFunctionContext):
        pass


    # Enter a parse tree produced by MFLangParser#llvFunction.
    def enterLlvFunction(self, ctx:MFLangParser.LlvFunctionContext):
        pass

    # Exit a parse tree produced by MFLangParser#llvFunction.
    def exitLlvFunction(self, ctx:MFLangParser.LlvFunctionContext):
        pass


    # Enter a parse tree produced by MFLangParser#hhvbarsFunction.
    def enterHhvbarsFunction(self, ctx:MFLangParser.HhvbarsFunctionContext):
        pass

    # Exit a parse tree produced by MFLangParser#hhvbarsFunction.
    def exitHhvbarsFunction(self, ctx:MFLangParser.HhvbarsFunctionContext):
        pass


    # Enter a parse tree produced by MFLangParser#llvbarsFunction.
    def enterLlvbarsFunction(self, ctx:MFLangParser.LlvbarsFunctionContext):
        pass

    # Exit a parse tree produced by MFLangParser#llvbarsFunction.
    def exitLlvbarsFunction(self, ctx:MFLangParser.LlvbarsFunctionContext):
        pass


    # Enter a parse tree produced by MFLangParser#countFunction.
    def enterCountFunction(self, ctx:MFLangParser.CountFunctionContext):
        pass

    # Exit a parse tree produced by MFLangParser#countFunction.
    def exitCountFunction(self, ctx:MFLangParser.CountFunctionContext):
        pass


    # Enter a parse tree produced by MFLangParser#maxFunction.
    def enterMaxFunction(self, ctx:MFLangParser.MaxFunctionContext):
        pass

    # Exit a parse tree produced by MFLangParser#maxFunction.
    def exitMaxFunction(self, ctx:MFLangParser.MaxFunctionContext):
        pass


    # Enter a parse tree produced by MFLangParser#max1Function.
    def enterMax1Function(self, ctx:MFLangParser.Max1FunctionContext):
        pass

    # Exit a parse tree produced by MFLangParser#max1Function.
    def exitMax1Function(self, ctx:MFLangParser.Max1FunctionContext):
        pass


    # Enter a parse tree produced by MFLangParser#minFunction.
    def enterMinFunction(self, ctx:MFLangParser.MinFunctionContext):
        pass

    # Exit a parse tree produced by MFLangParser#minFunction.
    def exitMinFunction(self, ctx:MFLangParser.MinFunctionContext):
        pass


    # Enter a parse tree produced by MFLangParser#min1Function.
    def enterMin1Function(self, ctx:MFLangParser.Min1FunctionContext):
        pass

    # Exit a parse tree produced by MFLangParser#min1Function.
    def exitMin1Function(self, ctx:MFLangParser.Min1FunctionContext):
        pass


    # Enter a parse tree produced by MFLangParser#ifFunction.
    def enterIfFunction(self, ctx:MFLangParser.IfFunctionContext):
        pass

    # Exit a parse tree produced by MFLangParser#ifFunction.
    def exitIfFunction(self, ctx:MFLangParser.IfFunctionContext):
        pass


    # Enter a parse tree produced by MFLangParser#absFunction.
    def enterAbsFunction(self, ctx:MFLangParser.AbsFunctionContext):
        pass

    # Exit a parse tree produced by MFLangParser#absFunction.
    def exitAbsFunction(self, ctx:MFLangParser.AbsFunctionContext):
        pass


    # Enter a parse tree produced by MFLangParser#emaFunction.
    def enterEmaFunction(self, ctx:MFLangParser.EmaFunctionContext):
        pass

    # Exit a parse tree produced by MFLangParser#emaFunction.
    def exitEmaFunction(self, ctx:MFLangParser.EmaFunctionContext):
        pass


    # Enter a parse tree produced by MFLangParser#maFunction.
    def enterMaFunction(self, ctx:MFLangParser.MaFunctionContext):
        pass

    # Exit a parse tree produced by MFLangParser#maFunction.
    def exitMaFunction(self, ctx:MFLangParser.MaFunctionContext):
        pass


    # Enter a parse tree produced by MFLangParser#smaFunction.
    def enterSmaFunction(self, ctx:MFLangParser.SmaFunctionContext):
        pass

    # Exit a parse tree produced by MFLangParser#smaFunction.
    def exitSmaFunction(self, ctx:MFLangParser.SmaFunctionContext):
        pass


    # Enter a parse tree produced by MFLangParser#stdFunction.
    def enterStdFunction(self, ctx:MFLangParser.StdFunctionContext):
        pass

    # Exit a parse tree produced by MFLangParser#stdFunction.
    def exitStdFunction(self, ctx:MFLangParser.StdFunctionContext):
        pass


    # Enter a parse tree produced by MFLangParser#modFunction.
    def enterModFunction(self, ctx:MFLangParser.ModFunctionContext):
        pass

    # Exit a parse tree produced by MFLangParser#modFunction.
    def exitModFunction(self, ctx:MFLangParser.ModFunctionContext):
        pass


    # Enter a parse tree produced by MFLangParser#hvFunction.
    def enterHvFunction(self, ctx:MFLangParser.HvFunctionContext):
        pass

    # Exit a parse tree produced by MFLangParser#hvFunction.
    def exitHvFunction(self, ctx:MFLangParser.HvFunctionContext):
        pass


    # Enter a parse tree produced by MFLangParser#lvFunction.
    def enterLvFunction(self, ctx:MFLangParser.LvFunctionContext):
        pass

    # Exit a parse tree produced by MFLangParser#lvFunction.
    def exitLvFunction(self, ctx:MFLangParser.LvFunctionContext):
        pass


    # Enter a parse tree produced by MFLangParser#timeFunction.
    def enterTimeFunction(self, ctx:MFLangParser.TimeFunctionContext):
        pass

    # Exit a parse tree produced by MFLangParser#timeFunction.
    def exitTimeFunction(self, ctx:MFLangParser.TimeFunctionContext):
        pass


    # Enter a parse tree produced by MFLangParser#betweenFunction.
    def enterBetweenFunction(self, ctx:MFLangParser.BetweenFunctionContext):
        pass

    # Exit a parse tree produced by MFLangParser#betweenFunction.
    def exitBetweenFunction(self, ctx:MFLangParser.BetweenFunctionContext):
        pass


    # Enter a parse tree produced by MFLangParser#crossPeriodRef.
    def enterCrossPeriodRef(self, ctx:MFLangParser.CrossPeriodRefContext):
        pass

    # Exit a parse tree produced by MFLangParser#crossPeriodRef.
    def exitCrossPeriodRef(self, ctx:MFLangParser.CrossPeriodRefContext):
        pass


    # Enter a parse tree produced by MFLangParser#formatOption.
    def enterFormatOption(self, ctx:MFLangParser.FormatOptionContext):
        pass

    # Exit a parse tree produced by MFLangParser#formatOption.
    def exitFormatOption(self, ctx:MFLangParser.FormatOptionContext):
        pass


    # Enter a parse tree produced by MFLangParser#identifier.
    def enterIdentifier(self, ctx:MFLangParser.IdentifierContext):
        pass

    # Exit a parse tree produced by MFLangParser#identifier.
    def exitIdentifier(self, ctx:MFLangParser.IdentifierContext):
        pass


    # Enter a parse tree produced by MFLangParser#rgbFunction.
    def enterRgbFunction(self, ctx:MFLangParser.RgbFunctionContext):
        pass

    # Exit a parse tree produced by MFLangParser#rgbFunction.
    def exitRgbFunction(self, ctx:MFLangParser.RgbFunctionContext):
        pass


    # Enter a parse tree produced by MFLangParser#drawStatement.
    def enterDrawStatement(self, ctx:MFLangParser.DrawStatementContext):
        pass

    # Exit a parse tree produced by MFLangParser#drawStatement.
    def exitDrawStatement(self, ctx:MFLangParser.DrawStatementContext):
        pass


    # Enter a parse tree produced by MFLangParser#drawArg.
    def enterDrawArg(self, ctx:MFLangParser.DrawArgContext):
        pass

    # Exit a parse tree produced by MFLangParser#drawArg.
    def exitDrawArg(self, ctx:MFLangParser.DrawArgContext):
        pass


    # Enter a parse tree produced by MFLangParser#drawFunction.
    def enterDrawFunction(self, ctx:MFLangParser.DrawFunctionContext):
        pass

    # Exit a parse tree produced by MFLangParser#drawFunction.
    def exitDrawFunction(self, ctx:MFLangParser.DrawFunctionContext):
        pass


    # Enter a parse tree produced by MFLangParser#formatOnlyStatement.
    def enterFormatOnlyStatement(self, ctx:MFLangParser.FormatOnlyStatementContext):
        pass

    # Exit a parse tree produced by MFLangParser#formatOnlyStatement.
    def exitFormatOnlyStatement(self, ctx:MFLangParser.FormatOnlyStatementContext):
        pass



del MFLangParser